import { useMemo, useState, useCallback, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

import { useCases } from "../hooks/useCases";
import { useGmailOverview } from "../hooks/useGmailOverview";
import { useAnalyzeGmailMessage } from "../hooks/useAnalyzeGmailMessage";
import { useCaseContext } from "../context/CaseContext";

import DashboardSections from "../components/dashboard/DashboardSections";


// How many of the most recently loaded Gmail messages to silently
// analyze on first load so the dashboard's charts/cards have real
// data instead of empty states. Kept small since each one is a
// full backend analyze call.
const AUTO_ANALYZE_COUNT = 5;


/* =========================================================
   HELPERS
   ========================================================= */

function isSameDay(value, referenceDate) {
  if (!value) return false;

  const date = new Date(value);
  const now = referenceDate || new Date();

  return (
    date.getDate() === now.getDate() &&
    date.getMonth() === now.getMonth() &&
    date.getFullYear() === now.getFullYear()
  );
}


function startOfDay(value) {
  const date = new Date(value);
  date.setHours(0, 0, 0, 0);
  return date;
}


function getDailyBreakdown(cases, referenceDate) {
  const days = 7;
  const now = referenceDate || new Date();

  return Array.from(
    { length: days },
    (_, index) => {
      const date = new Date(now);

      date.setDate(
        now.getDate() - (days - 1 - index)
      );

      const dayCases = cases.filter((item) => {
        if (!item?.analyzedAt) return false;

        const analyzed = new Date(item.analyzedAt);

        return (
          analyzed.getDate() === date.getDate() &&
          analyzed.getMonth() === date.getMonth() &&
          analyzed.getFullYear() === date.getFullYear()
        );
      });

      return {
        label: date.toLocaleDateString(
          [],
          { weekday: "short" }
        ),

        red: dayCases.filter(
          (c) => c?.severity === "red"
        ).length,

        yellow: dayCases.filter(
          (c) => c?.severity === "yellow"
        ).length,

        green: dayCases.filter(
          (c) => c?.severity === "green"
        ).length,

        reviewed: dayCases.filter(
          (c) => c?.reviewed === true
        ).length,

        pending: dayCases.filter(
          (c) => c?.reviewed !== true
        ).length,
      };
    }
  );
}


function getChartData(cases, referenceDate) {
  const days = 7;
  const now = referenceDate || new Date();

  return Array.from(
    { length: days },
    (_, index) => {
      const date = new Date(now);

      date.setDate(
        now.getDate() - (days - 1 - index)
      );

      const dayCases = cases.filter((item) => {
        if (!item?.analyzedAt) return false;

        const analyzed = new Date(item.analyzedAt);

        return (
          analyzed.getDate() === date.getDate() &&
          analyzed.getMonth() === date.getMonth() &&
          analyzed.getFullYear() === date.getFullYear()
        );
      });

      return {
        date,

        label: date.toLocaleDateString(
          [],
          { weekday: "short" }
        ),

        total: dayCases.length,

        red: dayCases.filter(
          (item) => item?.severity === "red"
        ).length,

        yellow: dayCases.filter(
          (item) => item?.severity === "yellow"
        ).length,

        green: dayCases.filter(
          (item) => item?.severity === "green"
        ).length,
      };
    }
  );
}


/* =========================================================
   GMAIL MERGE HELPERS
   ========================================================= */

function mergeTopDomains(
  caseDomains,
  gmailDomains,
  limit = 5
) {
  const counts = new Map();

  [
    ...(caseDomains || []),
    ...(gmailDomains || []),
  ].forEach(({ domain, count }) => {
    if (!domain) return;

    counts.set(
      domain,
      (counts.get(domain) || 0) +
        Number(count || 0)
    );
  });

  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([domain, count]) => ({
      domain,
      count,
    }));
}


function getMailboxActivityByWeekday(
  gmailActivity
) {
  const byWeekday = new Map();

  (gmailActivity || []).forEach((item) => {
    if (!item?.date) return;

    const date = new Date(item.date);

    if (Number.isNaN(date.getTime())) return;

    const label = date.toLocaleDateString(
      [],
      { weekday: "short" }
    );

    byWeekday.set(
      label,
      (byWeekday.get(label) || 0) +
        Number(item.count || 0)
    );
  });

  return byWeekday;
}


const AUTH_PROTOCOLS = [
  "spf",
  "dkim",
  "dmarc",
];


function getAuthBreakdown(cases) {
  const totals = {
    spf: {
      pass: 0,
      fail: 0,
      total: 0,
    },

    dkim: {
      pass: 0,
      fail: 0,
      total: 0,
    },

    dmarc: {
      pass: 0,
      fail: 0,
      total: 0,
    },
  };

  let passChecks = 0;
  let ranChecks = 0;

  cases.forEach((item) => {
    const checks =
      item?.headerChecks ||
      item?.dashboard?.authentication ||
      {};

    AUTH_PROTOCOLS.forEach((key) => {
      let value = checks[key];

      if (
        typeof checks[key] === "object" &&
        checks[key] !== null
      ) {
        value = checks[key].result;
      }

      if (
        value !== "pass" &&
        value !== "fail"
      ) {
        return;
      }

      totals[key].total += 1;
      ranChecks += 1;

      if (value === "pass") {
        totals[key].pass += 1;
        passChecks += 1;
      } else {
        totals[key].fail += 1;
      }
    });
  });

  const passRate = ranChecks
    ? Math.round(
        (passChecks / ranChecks) * 100
      )
    : 0;

  return {
    totals,
    passRate,
    ranChecks,
  };
}


function getHighlightTrend(cases, referenceDate) {
  const days = 7;
  const now = referenceDate || new Date();

  return Array.from(
    { length: days },
    (_, index) => {
      const date = new Date(now);

      date.setDate(
        now.getDate() - (days - 1 - index)
      );

      const dayCases = cases.filter((item) => {
        if (!item?.analyzedAt) return false;

        const analyzed = new Date(item.analyzedAt);

        return (
          analyzed.getDate() === date.getDate() &&
          analyzed.getMonth() === date.getMonth() &&
          analyzed.getFullYear() === date.getFullYear()
        );
      });

      let high = 0;
      let medium = 0;
      let low = 0;

      dayCases.forEach((item) => {
        (
          item?.highlights ||
          item?.dashboard?.findings ||
          []
        ).forEach((finding) => {
          const level =
            finding?.level ||
            finding?.severity ||
            "medium";

          if (
            level === "high" ||
            level === "red"
          ) {
            high += 1;
          } else if (
            level === "low" ||
            level === "green"
          ) {
            low += 1;
          } else {
            medium += 1;
          }
        });
      });

      return {
        label: date.toLocaleDateString(
          [],
          { weekday: "short" }
        ),

        high,
        medium,
        low,
      };
    }
  );
}


function extractDomain(item) {
  const raw =
    item?.senderDomain ||
    item?.parsedEmail?.from ||
    item?.sender ||
    item?.from ||
    item?.analysis?.metadata?.from ||
    item?.analysis?.from ||
    "";

  const match =
    String(raw).match(
      /@([^\s>]+)/
    );

  const domain = match
    ? match[1]
    : raw;

  return domain
    ? domain
        .toLowerCase()
        .replace(/[<>]/g, "")
    : null;
}


function getTopSenderDomains(
  cases,
  limit = 5
) {
  const counts = new Map();

  cases.forEach((item) => {
    const domain = extractDomain(item);

    if (!domain) return;

    counts.set(
      domain,
      (counts.get(domain) || 0) + 1
    );
  });

  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([domain, count]) => ({
      domain,
      count,
    }));
}


/* =========================================================
   REAL ANALYZER AGGREGATION
   ========================================================= */

function getAnalyzerDashboard(cases) {
  const analyzedCases = cases.filter(
    (item) =>
      item?.dashboard ||
      item?.analysis
  );

  const empty = {
    metrics: {
      urlCount: 0,
      suspiciousUrlCount: 0,
      attachmentCount: 0,
      suspiciousAttachmentCount: 0,
      headerFindingCount: 0,
      receivedHopCount: 0,
      authenticationFailureCount: 0,
      totalFindingCount: 0,
    },

    authentication: [
      {
        name: "SPF",
        result: "none",
        status: "unknown",
        value: 0,
      },
      {
        name: "DKIM",
        result: "none",
        status: "unknown",
        value: 0,
      },
      {
        name: "DMARC",
        result: "none",
        status: "unknown",
        value: 0,
      },
    ],

    threatCategories: [],
    findingSeverity: [],
    contentRisk: [],
    findings: [],
  };

  if (!analyzedCases.length) {
    return empty;
  }

  const metrics = {
    ...empty.metrics,
  };

  const auth = {
    spf: {
      pass: 0,
      fail: 0,
      none: 0,
    },

    dkim: {
      pass: 0,
      fail: 0,
      none: 0,
    },

    dmarc: {
      pass: 0,
      fail: 0,
      none: 0,
    },
  };

  const categories = new Map();

  const severities = {
    low: 0,
    medium: 0,
    high: 0,
  };

  const content = {
    URLs: {
      total: 0,
      suspicious: 0,
    },

    Attachments: {
      total: 0,
      suspicious: 0,
    },

    "Header Findings": {
      total: 0,
      suspicious: 0,
    },
  };

  const findings = [];

  analyzedCases.forEach((item) => {
    const dashboard =
      item?.dashboard || {};

    const itemMetrics =
      dashboard?.metrics || {};

    metrics.urlCount += Number(
      itemMetrics.urlCount ||
      dashboard?.contentRisk?.find(
        (x) => x?.name === "URLs"
      )?.total ||
      item?.analysis?.urls?.length ||
      0
    );

    metrics.suspiciousUrlCount += Number(
      itemMetrics.suspiciousUrlCount ||
      dashboard?.contentRisk?.find(
        (x) => x?.name === "URLs"
      )?.suspicious ||
      0
    );

    metrics.attachmentCount += Number(
      itemMetrics.attachmentCount ||
      dashboard?.contentRisk?.find(
        (x) => x?.name === "Attachments"
      )?.total ||
      item?.analysis?.attachments?.length ||
      0
    );

    metrics.suspiciousAttachmentCount += Number(
      itemMetrics.suspiciousAttachmentCount ||
      dashboard?.contentRisk?.find(
        (x) => x?.name === "Attachments"
      )?.suspicious ||
      0
    );

    metrics.headerFindingCount += Number(
      itemMetrics.headerFindingCount ||
      dashboard?.contentRisk?.find(
        (x) => x?.name === "Header Findings"
      )?.total ||
      item?.analysis?.header_findings?.length ||
      0
    );

    metrics.receivedHopCount += Number(
      itemMetrics.receivedHopCount ||
      item?.analysis?.received_chain?.length ||
      0
    );

    metrics.authenticationFailureCount += Number(
      itemMetrics.authenticationFailureCount ||
      0
    );

    metrics.totalFindingCount += Number(
      itemMetrics.totalFindingCount ||
      dashboard?.findings?.length ||
      0
    );

    AUTH_PROTOCOLS.forEach((protocol) => {
      const result =
        item?.headerChecks?.[protocol] ||
        item?.analysis?.authentication?.[protocol]?.result ||
        "none";

      if (
        auth[protocol][result] !== undefined
      ) {
        auth[protocol][result] += 1;
      } else {
        auth[protocol].none += 1;
      }
    });

    (
      dashboard?.threatCategories ||
      []
    ).forEach((entry) => {
      const key =
        entry?.name || "Other";

      categories.set(
        key,
        (categories.get(key) || 0) +
          Number(entry?.value || 0)
      );
    });

    (
      dashboard?.findingSeverity ||
      []
    ).forEach((entry) => {
      const name =
        String(
          entry?.name || ""
        ).toLowerCase();

      if (
        name === "high" ||
        name === "critical"
      ) {
        severities.high += Number(
          entry?.value || 0
        );
      } else if (
        name === "medium" ||
        name === "moderate"
      ) {
        severities.medium += Number(
          entry?.value || 0
        );
      } else {
        severities.low += Number(
          entry?.value || 0
        );
      }
    });

    (
      dashboard?.findings ||
      item?.analysis?.header_findings ||
      []
    ).forEach((finding) => {
      findings.push({
        ...finding,
        caseId: item?.caseId,
      });
    });
  });

  content.URLs.total =
    metrics.urlCount;

  content.URLs.suspicious =
    metrics.suspiciousUrlCount;

  content.Attachments.total =
    metrics.attachmentCount;

  content.Attachments.suspicious =
    metrics.suspiciousAttachmentCount;

  content["Header Findings"].total =
    metrics.headerFindingCount;

  content["Header Findings"].suspicious =
    metrics.headerFindingCount;

  return {
    metrics,

    authentication:
      AUTH_PROTOCOLS.map((protocol) => ({
        name: protocol.toUpperCase(),

        result:
          auth[protocol].fail > 0
            ? "fail"
            : auth[protocol].pass > 0
              ? "pass"
              : "none",

        status:
          auth[protocol].fail > 0
            ? "fail"
            : auth[protocol].pass > 0
              ? "pass"
              : "unknown",

        value:
          auth[protocol].pass,
      })),

    threatCategories:
      [...categories.entries()]
        .map(([name, value]) => ({
          name,
          value,
        }))
        .sort(
          (a, b) => b.value - a.value
        ),

    findingSeverity: [
      {
        name: "High",
        value: severities.high,
      },
      {
        name: "Medium",
        value: severities.medium,
      },
      {
        name: "Low",
        value: severities.low,
      },
    ],

    contentRisk:
      Object.entries(content)
        .map(([name, value]) => ({
          name,
          ...value,
        })),

    findings,
  };
}


/* =========================================================
   PAGE
   ========================================================= */

export default function DashboardPage() {
  const navigate = useNavigate();

  const {
    currentCase,
    setCurrentCase,
  } = useCaseContext();

  const {
    cases: fetchedCases,
    isLoading,
    error,
    refetch,
  } = useCases();

  const {
    status: gmailStatus,
    dashboard: gmailDashboard,
    connected: gmailConnected,
    isLoading: gmailIsLoading,
    isSyncing: gmailSyncing,
    loadProgress: gmailLoadProgress,
    error: gmailError,
    sync: syncGmailNow,
  } = useGmailOverview();

  const { analyze: analyzeGmailMessageFor } =
    useAnalyzeGmailMessage();

  // Declared up here (rather than next to the effect that fills
  // them) because dashboardCases below needs to read
  // autoAnalyzedCases, and hooks/consts must be initialized before
  // the code that references them runs.
  const autoAnalyzeRanRef = useRef(false);
  const [autoAnalyzeStatus, setAutoAnalyzeStatus] =
    useState(null); // { done, total } while running, else null
  const [autoAnalyzedCases, setAutoAnalyzedCases] = useState([]);


  /* =======================================================
     SELECTED DATE
     ======================================================= */

  const [selectedDate, setSelectedDate] = useState(
    () => startOfDay(new Date())
  );

  const isViewingToday = isSameDay(
    selectedDate,
    new Date()
  );

  const goToPreviousDay = useCallback(() => {
    setSelectedDate((current) => {
      const next = new Date(current);
      next.setDate(current.getDate() - 1);
      return next;
    });
  }, []);

  const goToNextDay = useCallback(() => {
    setSelectedDate((current) => {
      if (isSameDay(current, new Date())) {
        return current;
      }

      const next = new Date(current);
      next.setDate(current.getDate() + 1);
      return next;
    });
  }, []);

  const selectedDateLabel = isViewingToday
    ? "Today"
    : selectedDate.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });


  /* =======================================================
     CASE DATA
     ======================================================= */

  const cases = Array.isArray(
    fetchedCases
  )
    ? fetchedCases
    : [];


  /*
   * The freshly analyzed case can contain the complete dashboard
   * response before the case-list endpoint has refreshed. And
   * GET /cases itself never carries `headerChecks`/`dashboard`/
   * `analysis` at all (see the auto-analyze note below) — only a
   * direct analyze response does.
   *
   * So: start from the list, then layer the full-detail versions
   * (currentCase + anything the background auto-analyze produced)
   * on top by caseId, instead of just appending currentCase.
   */

  const dashboardCases = useMemo(() => {
    const merged = new Map();

    cases.forEach((item) => {
      if (item?.caseId) merged.set(item.caseId, item);
    });

    autoAnalyzedCases.forEach((item) => {
      if (!item?.caseId) return;
      merged.set(item.caseId, {
        ...merged.get(item.caseId),
        ...item,
      });
    });

    if (currentCase?.caseId) {
      merged.set(currentCase.caseId, {
        ...merged.get(currentCase.caseId),
        ...currentCase,
      });
    }

    return Array.from(merged.values());
  }, [
    cases,
    autoAnalyzedCases,
    currentCase,
  ]);


  /* =======================================================
     GMAIL
     ======================================================= */

  const mailboxStats =
    gmailDashboard?.stats || {};

  const mailboxActivityByWeekday =
    useMemo(
      () =>
        getMailboxActivityByWeekday(
          gmailConnected
            ? gmailDashboard?.activity
            : []
        ),
      [
        gmailConnected,
        gmailDashboard,
      ]
    );


  /* =======================================================
     AUTO-ANALYZE (background, data-only)

     If Gmail is connected but none of the loaded cases carry
     real analyzer output yet, silently run a handful of the
     most recently loaded mailbox messages through the same
     analyze pipeline as a manual upload. This is purely to
     seed the dashboard's charts/cards with real data — it
     never sets `currentCase` and never navigates away.

     (autoAnalyzeRanRef / autoAnalyzeStatus / autoAnalyzedCases
     are declared up near the top of the component — see the
     comment there — since dashboardCases needs to read
     autoAnalyzedCases before this effect runs.)
     ======================================================= */

  useEffect(() => {
    if (autoAnalyzeRanRef.current) return;
    if (isLoading || gmailIsLoading) return;
    if (!gmailConnected) return;

    const messages = gmailDashboard?.messages || [];
    if (!messages.length) return;

    // Only seed once — check for real analyzer detail
    // (`.dashboard`/`.analysis`/`.headerChecks`), not just any case
    // existing. Pre-existing cases from GET /cases are lightweight
    // (riskScore/severity/reviewed/analyzedAt only — see the note
    // above), so a case can exist in history while still carrying
    // none of the detail these three cards need. dashboardCases
    // also folds in autoAnalyzedCases/currentCase, so once a real
    // seed has actually landed this correctly stops re-running.
    const hasRealDetail = dashboardCases.some(
      (item) =>
        item?.dashboard ||
        item?.analysis ||
        item?.headerChecks
    );
    if (hasRealDetail) return;

    autoAnalyzeRanRef.current = true;

    const targets = messages.slice(0, AUTO_ANALYZE_COUNT);

    (async () => {
      setAutoAnalyzeStatus({
        done: 0,
        total: targets.length,
      });

      const results = [];

      for (let i = 0; i < targets.length; i++) {
        try {
          const result = await analyzeGmailMessageFor(
            targets[i].id
          );
          if (result) results.push(result);
        } catch {
          // Skip messages that fail to analyze (e.g. malformed
          // MIME) — this is best-effort background seeding, not
          // a user-facing action.
        }

        setAutoAnalyzeStatus({
          done: i + 1,
          total: targets.length,
        });
      }

      if (results.length) {
        setAutoAnalyzedCases(results);
      }

      await refetch();
      setAutoAnalyzeStatus(null);
    })();
  }, [
    isLoading,
    gmailIsLoading,
    gmailConnected,
    gmailDashboard,
    dashboardCases,
    analyzeGmailMessageFor,
    refetch,
  ]);


  /* =======================================================
     CHART DATA
     ======================================================= */

  const chartData = useMemo(
    () =>
      getChartData(
        dashboardCases,
        selectedDate
      ).map((day) => ({
        ...day,

        mailboxTotal:
          mailboxActivityByWeekday.get(
            day.label
          ) || 0,
      })),
    [
      dashboardCases,
      mailboxActivityByWeekday,
      selectedDate,
    ]
  );


  const breakdownData = useMemo(
    () =>
      getDailyBreakdown(
        dashboardCases,
        selectedDate
      ),
    [dashboardCases, selectedDate]
  );


  const authBreakdown = useMemo(
    () =>
      getAuthBreakdown(
        dashboardCases
      ),
    [dashboardCases]
  );


  const highlightTrend = useMemo(
    () =>
      getHighlightTrend(
        dashboardCases,
        selectedDate
      ),
    [dashboardCases, selectedDate]
  );


  const caseTopDomains = useMemo(
    () =>
      getTopSenderDomains(
        dashboardCases
      ),
    [dashboardCases]
  );


  const topDomains = useMemo(
    () =>
      mergeTopDomains(
        caseTopDomains,
        gmailConnected
          ? gmailDashboard?.topDomains
          : []
      ),
    [
      caseTopDomains,
      gmailConnected,
      gmailDashboard,
    ]
  );


  /* =======================================================
     REAL ANALYZER DATA
     ======================================================= */

  const analyzerDashboard = useMemo(
    () =>
      getAnalyzerDashboard(
        dashboardCases
      ),
    [dashboardCases]
  );


  /* =======================================================
     STATISTICS
     ======================================================= */

  const totalFlags =
    analyzerDashboard.metrics
      .totalFindingCount ||
    dashboardCases.reduce(
      (sum, item) =>
        sum +
        (
          item?.highlights?.length ||
          0
        ),
      0
    );


  const todayCount =
    dashboardCases.filter(
      (item) =>
        isSameDay(
          item?.analyzedAt,
          selectedDate
        )
    ).length;


  const highRiskCount =
    dashboardCases.filter(
      (item) =>
        item?.severity === "red" ||
        Number(
          item?.riskScore || 0
        ) >= 80
    ).length;


  const reviewedCount =
    dashboardCases.filter(
      (item) =>
        item?.reviewed === true
    ).length;


  const averageScore =
    dashboardCases.length
      ? Math.round(
          dashboardCases.reduce(
            (sum, item) =>
              sum +
              Number(
                item?.riskScore || 0
              ),
            0
          ) /
            dashboardCases.length
        )
      : 0;


  const totalAlerts =
    chartData.reduce(
      (sum, item) =>
        sum + item.total,
      0
    );


  /* =======================================================
     GMAIL MERGE
     ======================================================= */

  const mailboxToday =
    gmailConnected
      ? Number(
          mailboxStats.today || 0
        )
      : 0;

  const mailboxThisWeek =
    gmailConnected
      ? Number(
          mailboxStats.thisWeek || 0
        )
      : 0;

  const mailboxTotalFetched =
    gmailConnected
      ? Number(
          mailboxStats.totalFetched || 0
        )
      : 0;

  const mailboxUnread =
    gmailConnected
      ? Number(
          mailboxStats.unread || 0
        )
      : 0;

  const mergedTodayCount =
    todayCount ||
    totalAlerts ||
    mailboxToday;

  const mergedReviewedCount =
    reviewedCount ||
    dashboardCases.length ||
    mailboxTotalFetched;

  const todayDelta =
    !todayCount &&
    gmailConnected
      ? `${mailboxThisWeek} mailbox this wk`
      : null;

  const reviewedDelta =
    !reviewedCount &&
    gmailConnected
      ? `${mailboxUnread} unread`
      : null;


  /* =======================================================
     RECENT CASES
     ======================================================= */

  const recentCases = [
    ...dashboardCases,
  ]
    .sort(
      (a, b) =>
        new Date(
          b?.analyzedAt || 0
        ) -
        new Date(
          a?.analyzedAt || 0
        )
    )
    .slice(0, 6);


  /* =======================================================
     LOADING
     ======================================================= */

  if (isLoading) {
    return (
      <main className="reference-dashboard">
        <div className="reference-shell">
          <p className="ref-history-note">
            Loading dashboard…
          </p>
        </div>
      </main>
    );
  }


  /* =======================================================
     ERROR
     ======================================================= */

  if (error) {
    return (
      <main className="reference-dashboard">
        <div className="reference-shell">
          <p className="ref-history-note">
            Couldn't load cases:{" "}
            {error}
          </p>
        </div>
      </main>
    );
  }


  /* =======================================================
     RENDER
     ======================================================= */

  return (
    <main className="reference-dashboard">
      <div className="reference-shell">

        <DashboardSections
          navigate={
            navigate
          }

          cases={
            dashboardCases
          }

          selectedDateLabel={
            selectedDateLabel
          }

          onPrevDate={
            goToPreviousDay
          }

          onNextDate={
            goToNextDay
          }

          isNextDateDisabled={
            isViewingToday
          }

          chartData={
            chartData
          }

          breakdownData={
            breakdownData
          }

          authBreakdown={
            authBreakdown
          }

          highlightTrend={
            highlightTrend
          }

          topDomains={
            topDomains
          }

          totalFlags={
            totalFlags
          }

          todayCount={
            mergedTodayCount
          }

          todayDelta={
            todayDelta
          }

          highRiskCount={
            highRiskCount
          }

          reviewedCount={
            mergedReviewedCount
          }

          reviewedDelta={
            reviewedDelta
          }

          averageScore={
            averageScore
          }

          totalAlerts={
            totalAlerts
          }

          /* New real analyzer information */
          analyzerDashboard={
            analyzerDashboard
          }

          gmailStatus={
            gmailStatus
          }

          gmailConnected={
            gmailConnected
          }

          gmailSyncing={
            gmailSyncing
          }

          gmailLoadProgress={
            gmailLoadProgress
          }

          gmailError={
            gmailError
          }

          autoAnalyzeStatus={
            autoAnalyzeStatus
          }

          onSyncGmail={
            syncGmailNow
          }

          recentCases={
            recentCases
          }
        />

      </div>
    </main>
  );
}
