import { useOutletContext } from 'react-router-dom'

const DashboardOverview = () => {
  const outletContext = useOutletContext() || {}
  const { tableCount, ping, pingTime, pingError } = outletContext

  return (
    <>
      <header className="content-headline">
        <h1>Hey there!</h1>
        <p className="lede">
          Welcome back! Select an administrative module from the glass menu to get started.
        </p>
      </header>

      <section className="content-panels">
        <article className="glass-panel">
          <h3>Live schema insights</h3>
          <p>
            This workspace mirrors your database schema. Updates to the backend automatically
            populate the admin navigator on the left, keeping configuration in sync.
          </p>
        </article>
        <article className="glass-panel">
          <h3>Next steps</h3>
          <ul>
            <li>Pick a module from the sidebar.</li>
            <li>Review permissions and workflows.</li>
            <li>Iterate on the dashboard content area.</li>
          </ul>
        </article>
        <article className="glass-panel ping-panel">
          <p className="ping-label">Server stats</p>
          {ping ? (
            <>
              <p className="ping-time">{pingTime !== null ? `${pingTime} ms` : 'Measuring latency...'}</p>
              <p className="ping-meta">Tables tracked: {tableCount !== null ? tableCount : 'Unavailable'}</p>
            </>
          ) : (
            <p className="ping-state">{pingError || 'Checking server availability...'}</p>
          )}
        </article>
      </section>
    </>
  )
}

export default DashboardOverview
