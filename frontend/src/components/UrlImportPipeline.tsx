const DEFAULT_PIPELINE = [
  'download',
  'parse',
  'preview',
  'import',
  'finished',
] as const

const DEFAULT_LABELS: Record<string, string> = {
  download: 'Download',
  parse: 'Parse',
  preview: 'Preview',
  import: 'Import',
  finished: 'Finished',
}

type Props = {
  pipeline?: string[]
  labels?: Record<string, string>
  currentStage?: string | null
  stagesRun?: string[]
}

export default function UrlImportPipeline({
  pipeline = [...DEFAULT_PIPELINE],
  labels = DEFAULT_LABELS,
  currentStage = null,
  stagesRun = [],
}: Props) {
  const currentIndex = currentStage ? pipeline.indexOf(currentStage) : -1
  const completed = new Set(stagesRun)

  return (
    <ol
      className="url-pipeline"
      aria-label="Pipeline progress"
      style={{
        gridTemplateColumns: `repeat(${pipeline.length}, minmax(0, 1fr))`,
      }}
    >
      {pipeline.map((stage, index) => {
        const done =
          completed.has(stage) || (currentIndex >= 0 && index < currentIndex)
        const active = stage === currentStage
        const className = [
          'url-pipeline-step',
          done ? 'done' : '',
          active ? 'active' : '',
        ]
          .filter(Boolean)
          .join(' ')
        return (
          <li key={stage} className={className}>
            <span className="url-pipeline-dot" aria-hidden="true" />
            <span className="url-pipeline-label">
              {labels[stage] || stage}
            </span>
            {index < pipeline.length - 1 && (
              <span className="url-pipeline-arrow" aria-hidden="true">
                →
              </span>
            )}
          </li>
        )
      })}
    </ol>
  )
}

export { DEFAULT_LABELS, DEFAULT_PIPELINE }
