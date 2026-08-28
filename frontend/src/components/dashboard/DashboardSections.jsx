import {
  AlertTriangle,
  CalendarDays,
  ChevronDown,
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
  UploadEmailCard,
  RiskGauge,
  AlertVolumeChart,
  BreakdownChart,
  OperationsChart,
  AuthHealthChips,
  FlaggedSectionsChart,
  TopSenderDomains,
} from "./DashboardWidgets";

import EmailParsingPanel from "./EmailParsingPanel";
import DashboardAlertQueue from "./DashboardAlertQueue";


export default function DashboardSections({
  currentCase,
  setCurrentCase,

  handleFileSelected,
  isAnalyzing,
  analyzeError,

  navigate,

  cases,
  chartData,
  breakdownData,
  authBreakdown,
  highlightTrend,
  topDomains,

  totalFlags,
  todayCount,
  todayDelta,
  highRiskCount,
  reviewedCount,
  reviewedDelta,
  averageScore,
  totalAlerts,
  recentCases,

  gmailStatus,
  gmailConnected,
  gmailSyncing,
  gmailLoadProgress,
  gmailError,
  onSyncGmail,
}) {
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
          >
            <ChevronLeft size={17} />
          </button>

          <span className="ref-date-top">
            Sept 30
          </span>

          <button
            type="button"
            className="ref-icon-button"
            aria-label="Next date"
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


      {/* =================================================
          EMAIL UPLOAD / ANALYSIS
          ================================================= */}

      <UploadEmailCard
        onFileSelected={handleFileSelected}
        isLoading={isAnalyzing}
      />

      {analyzeError && (
        <p className="ref-history-note">
          Couldn't analyze that email:{" "}
          {analyzeError}
        </p>
      )}


      {/* =================================================
          CURRENT EMAIL PARSING
          ================================================= */}

      <EmailParsingPanel
        currentCase={currentCase}
      />


      {/* =================================================
          TOOLBAR
          ================================================= */}

      <div className="reference-toolbar">
        <div className="ref-search">
          <span>
            Alert Queue
          </span>
        </div>

        <button
          type="button"
          className="ref-date-picker"
        >
          <CalendarDays size={16} />

          Sept 30

          <ChevronDown size={15} />
        </button>
      </div>


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

        {/* Authentication */}

        <DashboardPanel
          title="Authentication Health"
          right={
            <span className="ref-panel-number">
              {authBreakdown.ranChecks ||
                cases.length}
            </span>
          }
        >
          <div className="ref-firewall-number">
            {cases.length
              ? `${cases.length} emails scanned`
              : "0 emails scanned"}
          </div>

          <RiskGauge
            value={
              authBreakdown.ranChecks
                ? authBreakdown.passRate
                : 92
            }
            caption="SPF / DKIM / DMARC pass rate"
          />

          <span className="ref-history-note">
            {authBreakdown.totals.spf.fail +
              authBreakdown.totals.dkim.fail +
              authBreakdown.totals.dmarc.fail}{" "}
            failed checks
          </span>

          <AuthHealthChips
            totals={authBreakdown.totals}
          />
        </DashboardPanel>


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


        {/* Breakdown */}

        <DashboardPanel
          title="Breakdown"
          right={
            <button
              type="button"
              className="ref-week"
            >
              Week
              <ChevronDown size={13} />
            </button>
          }
        >
          <BreakdownChart
            variant="one"
            data={breakdownData}
          />
        </DashboardPanel>

      </div>


      {/* =================================================
          SECOND CHART ROW
          ================================================= */}

      <div className="ref-grid-two">

        <DashboardPanel
          title="Breakdown"
          right={
            <button
              type="button"
              className="ref-week"
            >
              Week
              <ChevronDown size={13} />
            </button>
          }
        >
          <BreakdownChart
            variant="two"
            data={breakdownData}
          />
        </DashboardPanel>


        <DashboardPanel
          title="Verdict Trend"
          right={
            <button
              type="button"
              className="ref-week"
            >
              Week
              <ChevronDown size={13} />
            </button>
          }
        >
          <OperationsChart
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
          <FlaggedSectionsChart
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
