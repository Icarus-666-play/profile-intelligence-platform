"""BeautifulSoup-based EuroGirls HTML extractor.

Produces typed structured data only — no persistence / SQL.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from eurogirls.parser import ParsedWebArchive, WebSubresource
from profile_intelligence.core.logging import get_logger
from profile_intelligence.infrastructure.media.hashing import hash_bytes

logger = get_logger("importers.external.eurogirls.extractor")

_LABEL_ALIASES: dict[str, tuple[str, ...]] = {
    "name": ("name", "profile name", "escort name", "model"),
    "profile_id": ("profile id", "id", "member id", "eg id", "ref"),
    "country": ("country", "nation"),
    "city": ("city", "town", "location city"),
    "nationality": ("nationality", "origin"),
    "languages": ("languages", "language", "speaks"),
    "age": ("age",),
    "height": ("height",),
    "weight": ("weight",),
    "hair": ("hair", "hair colour", "hair color"),
    "eyes": ("eyes", "eye colour", "eye color"),
    "bust": ("bust", "cup", "cup size"),
    "measurements": ("measurements", "stats", "figure"),
}

_CURRENCY_RE = re.compile(
    r"(?P<currency>EUR|USD|GBP|CHF|€|\$|£)\s*(?P<price>\d+(?:[.,]\d{2})?)"
    r"|(?P<price2>\d+(?:[.,]\d{2})?)\s*(?P<currency2>EUR|USD|GBP|CHF|€|\$|£)",
    re.IGNORECASE,
)
_DURATION_RE = re.compile(
    r"(?P<duration>\d+\s*(?:min|mins|minutes|hour|hours|hr|hrs)"
    r"|overnight|dinner|weekend)",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class Rate:
    """One rate row extracted from a EuroGirls profile."""

    duration: str
    price: str
    currency: str
    incall: bool
    outcall: bool

    def to_mapping(self) -> dict[str, Any]:
        """Serialize for raw_json / repository payloads."""
        return {
            "duration": self.duration,
            "price": self.price,
            "currency": self.currency,
            "incall": self.incall,
            "outcall": self.outcall,
        }


@dataclass(frozen=True, slots=True)
class Service:
    """One offered service."""

    name: str
    available: bool = True

    def to_mapping(self) -> dict[str, Any]:
        """Serialize for raw_json / repository payloads."""
        return {"name": self.name, "available": self.available}


@dataclass(frozen=True, slots=True)
class Photo:
    """Profile photo metadata (content-addressed via SHA-256 when bytes exist)."""

    original_url: str
    sha256: str | None
    role: str  # main | gallery
    content_type: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        """Serialize for raw_json / repository payloads."""
        return {
            "original_url": self.original_url,
            "sha256": self.sha256,
            "role": self.role,
            "content_type": self.content_type,
        }


@dataclass(slots=True)
class ExtractedProfile:
    """Structured EuroGirls profile prior to platform normalization."""

    name: str | None = None
    profile_id: str | None = None
    url: str | None = None
    country: str | None = None
    city: str | None = None
    nationality: str | None = None
    languages: list[str] = field(default_factory=list)
    age: str | None = None
    height: str | None = None
    weight: str | None = None
    hair: str | None = None
    eyes: str | None = None
    bust: str | None = None
    measurements: str | None = None
    rates: list[Rate] = field(default_factory=list)
    services: list[Service] = field(default_factory=list)
    photos: list[Photo] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Minimum viable profile: display name present."""
        return bool(self.name and self.name.strip())


class EuroGirlsExtractor:
    """Extract structured fields from parsed EuroGirls HTML."""

    def __init__(self, *, hash_algorithm: str = "sha256") -> None:
        self._hash_algorithm = hash_algorithm

    def extract(self, archive: ParsedWebArchive) -> ExtractedProfile:
        """Parse HTML with BeautifulSoup and return structured data."""
        soup = BeautifulSoup(archive.html, "html.parser")
        profile = ExtractedProfile(url=archive.url)
        self._extract_identity(soup, profile, archive)
        self._extract_labeled_fields(soup, profile)
        if not profile.profile_id and archive.url:
            profile.profile_id = self._profile_id_from_url(archive.url)
        self._extract_rates(soup, profile)
        self._extract_services(soup, profile)
        self._extract_photos(soup, profile, archive.subresources)
        if not profile.is_complete:
            profile.warnings.append("missing profile name")
        if not profile.profile_id:
            profile.warnings.append("missing profile id")
        if not profile.rates:
            profile.warnings.append("no rates found")
        if not profile.services:
            profile.warnings.append("no services found")
        if not profile.photos:
            profile.warnings.append("no photos found")
        logger.info(
            "Extracted EuroGirls profile name=%r id=%r rates=%d services=%d "
            "photos=%d warnings=%d",
            profile.name,
            profile.profile_id,
            len(profile.rates),
            len(profile.services),
            len(profile.photos),
            len(profile.warnings),
        )
        return profile

    def _extract_identity(
        self,
        soup: BeautifulSoup,
        profile: ExtractedProfile,
        archive: ParsedWebArchive,
    ) -> None:
        heading = soup.select_one("h1.profile-name, h1.escort-name, h1")
        if heading is not None:
            profile.name = self._clean_text(heading.get_text(" ", strip=True))

        if not profile.name:
            title = soup.title.get_text(" ", strip=True) if soup.title else ""
            profile.name = self._clean_name_from_title(title)

        id_node = soup.select_one(
            ".profile-id, [data-profile-id], #profile-id, .member-id"
        )
        if id_node is not None:
            raw_id = id_node.get("data-profile-id") or id_node.get_text(
                " ", strip=True
            )
            profile.profile_id = self._normalize_profile_id(str(raw_id))

        og_url = soup.select_one('meta[property="og:url"]')
        if og_url and og_url.get("content"):
            profile.url = str(og_url["content"]).strip() or profile.url

    def _extract_labeled_fields(
        self,
        soup: BeautifulSoup,
        profile: ExtractedProfile,
    ) -> None:
        pairs = self._collect_label_value_pairs(soup)
        for field_name, aliases in _LABEL_ALIASES.items():
            if field_name == "name" and profile.name:
                continue
            if field_name == "profile_id" and profile.profile_id:
                continue
            value = self._lookup_alias(pairs, aliases)
            if value is None:
                continue
            if field_name == "languages":
                profile.languages = self._split_list(value)
            elif field_name == "name":
                profile.name = value
            elif field_name == "profile_id":
                profile.profile_id = self._normalize_profile_id(value)
            else:
                setattr(profile, field_name, value)

        city_node = soup.select_one(".city, [itemprop='addressLocality']")
        if city_node is not None and not profile.city:
            profile.city = self._clean_text(city_node.get_text(" ", strip=True))
        country_node = soup.select_one(".country, [itemprop='addressCountry']")
        if country_node is not None and not profile.country:
            profile.country = self._clean_text(
                country_node.get_text(" ", strip=True)
            )

    def _extract_rates(self, soup: BeautifulSoup, profile: ExtractedProfile) -> None:
        for row in soup.select(
            "table.rates tr[data-duration], .rates .rate-row, "
            "table.rates tbody tr"
        ):
            if not isinstance(row, Tag):
                continue
            if row.find("th") is not None and row.find("td") is None:
                continue
            rate = self._rate_from_element(row)
            if rate is not None:
                profile.rates.append(rate)

        if profile.rates:
            return

        # Fallback: scan rate list items / paragraphs.
        for node in soup.select(".rates li, .rate, .pricing li"):
            if not isinstance(node, Tag):
                continue
            rate = self._rate_from_text(node.get_text(" ", strip=True))
            if rate is not None:
                profile.rates.append(rate)

    def _extract_services(
        self,
        soup: BeautifulSoup,
        profile: ExtractedProfile,
    ) -> None:
        for node in soup.select(
            "ul.services li, .services li, .service-list li, "
            "[data-service], .services .service"
        ):
            if not isinstance(node, Tag):
                continue
            name = self._clean_text(
                str(node.get("data-service") or node.get_text(" ", strip=True))
            )
            if not name:
                continue
            available = "unavailable" not in name.lower()
            available_attr = node.get("data-available")
            if available_attr is not None:
                available = str(available_attr).lower() in {
                    "1",
                    "true",
                    "yes",
                }
            profile.services.append(Service(name=name, available=available))

    def _extract_photos(
        self,
        soup: BeautifulSoup,
        profile: ExtractedProfile,
        subresources: Sequence[WebSubresource],
    ) -> None:
        by_url = {item.url: item for item in subresources}
        main = soup.select_one(
            "img.main-photo, img.profile-photo, .main-photo img, "
            "meta[property='og:image']"
        )
        main_url = self._image_url(main, base=profile.url)
        seen: set[str] = set()
        if main_url:
            profile.photos.append(
                self._build_photo(main_url, role="main", by_url=by_url)
            )
            seen.add(main_url)

        for node in soup.select(
            ".gallery img, .photo-gallery img, ul.gallery img, "
            "img.gallery-photo"
        ):
            url = self._image_url(node, base=profile.url)
            if not url or url in seen:
                continue
            seen.add(url)
            profile.photos.append(
                self._build_photo(url, role="gallery", by_url=by_url)
            )

    def _build_photo(
        self,
        url: str,
        *,
        role: str,
        by_url: Mapping[str, WebSubresource],
    ) -> Photo:
        resource = by_url.get(url)
        digest: str | None = None
        content_type: str | None = None
        if resource is not None:
            digest = hash_bytes(
                resource.data, algorithm=self._hash_algorithm
            )
            content_type = resource.mime_type
        else:
            # Stable hash of the URL when bytes are unavailable.
            digest = hash_bytes(
                url.encode("utf-8"), algorithm=self._hash_algorithm
            )
        return Photo(
            original_url=url,
            sha256=digest,
            role=role,
            content_type=content_type,
        )

    def _rate_from_element(self, row: Tag) -> Rate | None:
        duration = str(row.get("data-duration") or "").strip()
        price = str(row.get("data-price") or "").strip()
        currency = str(row.get("data-currency") or "").strip().upper()
        incall = self._truthy(row.get("data-incall"))
        outcall = self._truthy(row.get("data-outcall"))

        cells = [
            self._clean_text(td.get_text(" ", strip=True))
            for td in row.find_all("td")
        ]
        text = " | ".join(cell for cell in cells if cell)
        if not duration or not price:
            parsed = self._rate_from_text(text)
            if parsed is None:
                return None
            duration = duration or parsed.duration
            price = price or parsed.price
            currency = currency or parsed.currency
            if row.get("data-incall") is None:
                incall = parsed.incall
            if row.get("data-outcall") is None:
                outcall = parsed.outcall

        if not duration or not price:
            return None
        if not currency:
            currency = "EUR"
        return Rate(
            duration=duration,
            price=price.replace(",", "."),
            currency=self._normalize_currency(currency),
            incall=incall,
            outcall=outcall,
        )

    def _rate_from_text(self, text: str) -> Rate | None:
        cleaned = self._clean_text(text)
        if not cleaned:
            return None
        duration_match = _DURATION_RE.search(cleaned)
        money_match = _CURRENCY_RE.search(cleaned)
        if duration_match is None or money_match is None:
            return None
        groups = money_match.groupdict()
        price = groups.get("price") or groups.get("price2") or ""
        currency = groups.get("currency") or groups.get("currency2") or "EUR"
        lower = cleaned.lower()
        incall = "incall" in lower or "in-call" in lower or "in call" in lower
        outcall = (
            "outcall" in lower or "out-call" in lower or "out call" in lower
        )
        if not incall and not outcall:
            incall = True
        return Rate(
            duration=duration_match.group("duration").strip(),
            price=price.replace(",", "."),
            currency=self._normalize_currency(currency),
            incall=incall,
            outcall=outcall,
        )

    @staticmethod
    def _collect_label_value_pairs(soup: BeautifulSoup) -> dict[str, str]:
        pairs: dict[str, str] = {}
        for row in soup.select("tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) < 2:
                continue
            label = cells[0].get_text(" ", strip=True).rstrip(":").strip().lower()
            value = cells[1].get_text(" ", strip=True)
            if label and value:
                pairs.setdefault(label, value)
        for node in soup.select("dt"):
            label = node.get_text(" ", strip=True).rstrip(":").strip().lower()
            sibling = node.find_next_sibling("dd")
            if label and sibling is not None:
                value = sibling.get_text(" ", strip=True)
                if value:
                    pairs.setdefault(label, value)
        for node in soup.select("[data-field]"):
            if not isinstance(node, Tag):
                continue
            label = str(node.get("data-field") or "").strip().lower()
            value = node.get_text(" ", strip=True)
            if label and value:
                pairs.setdefault(label, value)
        return pairs

    @staticmethod
    def _lookup_alias(
        pairs: Mapping[str, str],
        aliases: Sequence[str],
    ) -> str | None:
        for alias in aliases:
            if alias in pairs:
                return pairs[alias].strip()
        return None

    @staticmethod
    def _split_list(value: str) -> list[str]:
        parts = re.split(r"[,;/|]", value)
        return [part.strip() for part in parts if part.strip()]

    @staticmethod
    def _clean_text(value: str | None) -> str | None:
        if value is None:
            return None
        text = re.sub(r"\s+", " ", value).strip()
        return text or None

    @staticmethod
    def _clean_name_from_title(title: str) -> str | None:
        text = re.sub(r"\s+", " ", title).strip()
        if not text:
            return None
        for separator in (" | ", " - ", " — ", " · "):
            if separator in text:
                text = text.split(separator, 1)[0].strip()
                break
        lowered = text.lower()
        for noise in ("eurogirls", "escort", "profile"):
            if lowered == noise:
                return None
        return text or None

    @staticmethod
    def _normalize_profile_id(value: str) -> str | None:
        text = value.strip()
        text = re.sub(
            r"^(?:profile\s*)?id\s*[:#\-]?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        return text or None

    @staticmethod
    def _profile_id_from_url(url: str) -> str | None:
        path = urlparse(url).path.rstrip("/")
        if not path:
            return None
        slug = path.split("/")[-1]
        return slug or None

    @staticmethod
    def _image_url(node: Tag | None, *, base: str | None) -> str | None:
        if node is None:
            return None
        if node.name == "meta":
            raw = node.get("content")
        else:
            raw = node.get("src") or node.get("data-src")
        if not raw:
            return None
        url = str(raw).strip()
        if not url:
            return None
        if base:
            return urljoin(base, url)
        return url

    @staticmethod
    def _truthy(value: object | None) -> bool:
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "y"}

    @staticmethod
    def _normalize_currency(value: str) -> str:
        mapping = {"€": "EUR", "$": "USD", "£": "GBP"}
        cleaned = value.strip().upper()
        return mapping.get(cleaned, cleaned)
