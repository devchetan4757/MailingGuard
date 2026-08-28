import { useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { useCases } from "../hooks/useCases";
import { useGmailOverview } from "../hooks/useGmailOverview";
import { useCaseContext } from "../context/CaseContext";

import DashboardSections from "../components/dashboard/DashboardSections";


/* =========================================================
   HELPERS
   ========================================================= */

function isToday(value) {
  if (!value) return false;

  const date = new Date(value);
  const now = new Date();

  return (
    date.getDate() === now.getDate() &&
    date.getMonth() === now.getMonth() &&
    date.getFullYear() === now.getFullYear()
  );
}


function getDailyBreakdown(cases) {
  const days = 7;
  const now = new Date();

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


function getChartData(cases) {
  const days = 7;
  const now = new Date();

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


function getHighlightTrend(cases) {
  const days = 7;
  const now = new Date();

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
    isSyncing: gmailSyncing,
    loadProgress: gmailLoadProgress,
    error: gmailError,
    sync: syncGmailNow,
  } = useGmailOverview();


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
   * response before the case-list endpoint has refreshed.
   *
   * Include it immediately so the dashboard reacts to analysis
   * without waiting for another page load.
   */

  const dashboardCases = useMemo(() => {
    if (!currentCase?.caseId) {
      return cases;
    }

    const exists = cases.some(
      (item) =>
        item?.caseId ===
        currentCase.caseId
    );

    return exists
      ? cases
      : [
          ...cases,
          currentCase,
        ];
  }, [
    cases,
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
     CHART DATA
     ======================================================= */

  const chartData = useMemo(
    () =>
      getChartData(
        dashboardCases
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
    ]
  );


  const breakdownData = useMemo(
    () =>
      getDailyBreakdown(
        dashboardCases
      ),
    [dashboardCases]
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
        dashboardCases
      ),
    [dashboardCases]
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
        isToday(
          item?.analyzedAt
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
