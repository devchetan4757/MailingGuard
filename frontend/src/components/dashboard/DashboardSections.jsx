import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Mail,
  RefreshCw,
  ShieldCheck,
  Users,
} from "lucide-react";

import {
  DashboardPanel,
  DashboardStat,
  AlertVolumeChart,
  BreakdownChart,
  VerdictDonutChart,
  FlaggedSectionsBreakdown,
  ReviewProgressRing,
  TopSenderDomains,
  ThreatCategoryBars,
  ContentRiskPanel,
  AuthHealthChips,
} from "./DashboardWidgets";

import DashboardAlertQueue from "./DashboardAlertQueue";


export default function DashboardSections({
  navigate,

  cases,
  chartData,
  breakdownData,
  authBreakdown,
  highlightTrend,
  topDomains,
  analyzerDashboard,

  totalFlags,
  todayCount,
  todayDelta,
  highRiskCount,
  reviewedCount,
  reviewedDelta,
  averageScore,
  totalAlerts,
  recentCases,

  selectedDateLabel,
  onPrevDate,
  onNextDate,
  isNextDateDisabled,

  gmailStatus,
  gmailConnected,
  gmailSyncing,
  gmailLoadProgress,
  gmailError,
  autoAnalyzeStatus,
  onSyncGmail,
}) {
  const threatCategories =
    analyzerDashboard?.threatCategories || [];

  const contentRisk =
    analyzerDashboard?.contentRisk || [];

  const gmailIsChunkLoading = Boolean(gmailLoadProgress);

  const gmailPillLabel = gmailConnected
    ? gmailIsChunkLoading
      ? `Loading ${gmailLoadProgress.loaded}/${gmailLoadProgress.total}…`
      : gmailSyncing
        ? "Syncing…"
        : "Gmail synced"
    : "Connect Gmail";

  return (
    <>
      {/* =================================================
          HEADER
          ================================================= */}

      <header className="reference-page-head">
        <h1>
          Hello{" "}
          <span>Analyst</span>
        </h1>

        <div className="reference-head-actions">
          <button
            type="button"
            className="ref-icon-button"
            aria-label="Previous date"
            onClick={onPrevDate}
          >
            <ChevronLeft size={17} />
          </button>

          <span className="ref-date-top">
            {selectedDateLabel}
          </span>

          <button
            type="button"
            className="ref-icon-button"
            aria-label="Next date"
            onClick={onNextDate}
            disabled={isNextDateDisabled}
          >
            <ChevronRight size={17} />
          </button>

          {/* Gmail connection lives here as a compact
              status/sync control — mailbox numbers feed the
              cards and charts below rather than getting a
              section of their own. */}
          <button
            type="button"
            className={`ref-gmail-pill ${
              gmailConnected ? "is-connected" : ""
            }`}
            onClick={
              gmailConnected
                ? onSyncGmail
                : () => navigate("/gmail")
            }
            disabled={gmailSyncing || gmailIsChunkLoading}
            aria-label={
              gmailConnected
                ? "Sync Gmail"
                : "Connect Gmail"
            }
            title={
              gmailConnected
                ? gmailStatus?.profile?.email ||
                  gmailStatus?.email ||
                  "Sync Gmail"
                : "Connect Gmail"
            }
          >
            {gmailConnected ? (
              <RefreshCw
                size={13}
                className={
                  gmailSyncing || gmailIsChunkLoading
                    ? "ref-spin"
                    : ""
                }
              />
            ) : (
              <Mail size={13} />
            )}

            {gmailPillLabel}
          </button>

          <button
            type="button"
            className="ref-help"
            aria-label="Help"
          >
            <CircleHelp size={16} />
          </button>
        </div>
      </header>

      {gmailError && (
        <p className="ref-history-note">
          Gmail: {gmailError}
        </p>
      )}

      {autoAnalyzeStatus && (
        <p className="ref-history-note">
          Analyzing {autoAnalyzeStatus.done}/
          {autoAnalyzeStatus.total} recent emails to populate your
          dashboard…
        </p>
      )}

      {/* =================================================
          GMAIL LIVE LOAD STATUS
          ================================================= */}

      {gmailIsChunkLoading && (
        <section className="ref-mail-loading" aria-live="polite">
          <div className="ref-mail-loading-orbit" aria-hidden="true">
            <div className="ref-mail-loading-ring" />
            <Mail size={18} />
          </div>

          <div className="ref-mail-loading-copy">
            <div className="ref-mail-loading-title">
              Loading your mailbox
              <span className="ref-loading-dots" aria-hidden="true">
                <i />
                <i />
                <i />
              </span>
            </div>
            <p>
              Fetching Gmail messages and updating the dashboard in real time.
            </p>

            <div className="ref-mail-progress">
              <span
                style={{
                  width: `${Math.min(100, Math.max(0, (gmailLoadProgress.loaded / Math.max(gmailLoadProgress.total, 1)) * 100))}%`,
                }}
              />
            </div>
          </div>

          <div className="ref-mail-loading-count">
            <strong>{gmailLoadProgress.loaded}</strong>
            <span>/ {gmailLoadProgress.total}</span>
            <small>emails</small>
          </div>
        </section>
      )}


      {/* =================================================
          STATISTICS
          ================================================= */}

      <div className="ref-stats">
        <DashboardStat
          icon={AlertTriangle}
          label="Total Alerts (Today)"
          value={todayCount}
          delta={todayDelta || "-20%"}
        />

        <DashboardStat
          icon={AlertTriangle}
          label="Critical Incident"
          value={highRiskCount}
          delta="-30%"
        />

        <DashboardStat
          icon={Users}
          label="Emails Reviewed"
          value={reviewedCount}
          delta={reviewedDelta || "-50%"}
        />

        <DashboardStat
          icon={ShieldCheck}
          label="Avg Risk Score"
          value={averageScore}
          delta={`${authBreakdown.passRate}% auth pass`}
        />
      </div>


      {/* =================================================
          FIRST CHART ROW
          ================================================= */}

      <div className="ref-grid-three">

        {/* Alert Volume */}

        <DashboardPanel
          title="Alert Volume"
          right={
            <span className="ref-panel-number">
              {totalAlerts}
            </span>
          }
        >
          <AlertVolumeChart
            data={chartData}
          />
        </DashboardPanel>


        {/* Content Risk — real URL / attachment / header
            finding counts from the analyzer */}

        <DashboardPanel
          title="Content Risk"
        >
          <ContentRiskPanel
            data={contentRisk}
          />
        </DashboardPanel>


        {/* Authentication Health — real SPF/DKIM/DMARC
            pass rates, no placeholder numbers */}

        <DashboardPanel
          title="Authentication Health"
        >
          <AuthHealthChips
            totals={authBreakdown.totals}
          />

          <span className="ref-history-note">
            {authBreakdown.totals.spf.fail +
              authBreakdown.totals.dkim.fail +
              authBreakdown.totals.dmarc.fail}{" "}
            failed checks
          </span>
        </DashboardPanel>

      </div>


      {/* =================================================
          SECOND CHART ROW
          ================================================= */}

      <div className="ref-grid-two">

        <DashboardPanel
          title="Risk Severity Trend"
        >
          <BreakdownChart
            data={breakdownData}
          />
        </DashboardPanel>


        <DashboardPanel
          title="Verdict Breakdown"
        >
          <VerdictDonutChart
            data={breakdownData}
          />
        </DashboardPanel>

      </div>


      {/* =================================================
          THIRD CHART ROW
          ================================================= */}

      <div className="ref-grid-two">

        <DashboardPanel
          title="Flagged Sections"
          right={
            <span className="ref-panel-number">
              {totalFlags}
            </span>
          }
        >
          <FlaggedSectionsBreakdown
            data={highlightTrend}
          />
        </DashboardPanel>


        <DashboardPanel
          title="Top Sender Domains"
        >
          <TopSenderDomains
            data={topDomains}
          />
        </DashboardPanel>

      </div>


      {/* =================================================
          FOURTH CHART ROW
          ================================================= */}

      <div className="ref-grid-two">

        <DashboardPanel
          title="Threat Categories"
          right={
            <span className="ref-panel-number">
              {threatCategories.length}
            </span>
          }
        >
          <ThreatCategoryBars
            data={threatCategories}
          />
        </DashboardPanel>


        <DashboardPanel
          title="Review Progress"
        >
          <ReviewProgressRing
            data={breakdownData}
          />
        </DashboardPanel>

      </div>


      {/* =================================================
          ALERT QUEUE
          ================================================= */}

      <DashboardAlertQueue
        recentCases={recentCases}
        totalAlerts={totalAlerts}
        navigate={navigate}
      />


      {/* =================================================
          FOOTER
          ================================================= */}

      <footer className="reference-footer">
        <ShieldCheck size={14} />

        Powered by
        ThreadDetect AI
      </footer>
    </>
  );
}
