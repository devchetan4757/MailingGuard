import { useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { useCases } from "../hooks/useCases";
import { useAnalyzeEmail } from "../hooks/useAnalyzeEmail";
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
        now.getDate() -
          (days - 1 - index)
      );

      const dayCases = cases.filter(
        (item) => {
          if (!item?.analyzedAt) {
            return false;
          }

          const analyzed =
            new Date(item.analyzedAt);

          return (
            analyzed.getDate() ===
              date.getDate() &&
            analyzed.getMonth() ===
              date.getMonth() &&
            analyzed.getFullYear() ===
              date.getFullYear()
          );
        }
      );

      const red = dayCases.filter(
        (c) =>
          c?.severity === "red"
      ).length;

      const yellow = dayCases.filter(
        (c) =>
          c?.severity === "yellow"
      ).length;

      const green = dayCases.filter(
        (c) =>
          c?.severity === "green"
      ).length;

      const reviewed = dayCases.filter(
        (c) =>
          c?.reviewed === true
      ).length;

      const pending = dayCases.filter(
        (c) =>
          c?.reviewed !== true
      ).length;

      return {
        label: date.toLocaleDateString(
          [],
          { weekday: "short" }
        ),
        red,
        yellow,
        green,
        reviewed,
        pending,
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
        now.getDate() -
          (days - 1 - index)
      );

      const total = cases.filter(
        (item) => {
          if (!item?.analyzedAt) {
            return false;
          }

          const analyzed =
            new Date(item.analyzedAt);

          return (
            analyzed.getDate() ===
              date.getDate() &&
            analyzed.getMonth() ===
              date.getMonth() &&
            analyzed.getFullYear() ===
              date.getFullYear()
          );
        }
      ).length;

      return {
        date,
        label: date.toLocaleDateString(
          [],
          { weekday: "short" }
        ),
        total,
      };
    }
  );
}


/* =========================================================
   GMAIL MERGE HELPERS

   These fold mailbox data into the SAME widgets the case
   data already feeds (Top Sender Domains, Alert Volume,
   stat row) instead of standing up a parallel Gmail section.
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
    const hc =
      item?.headerChecks || {};

    AUTH_PROTOCOLS.forEach(
      (key) => {
        const value = hc[key];

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
      }
    );
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
        now.getDate() -
          (days - 1 - index)
      );

      const dayCases =
        cases.filter((item) => {
          if (!item?.analyzedAt) {
            return false;
          }

          const analyzed =
            new Date(item.analyzedAt);

          return (
            analyzed.getDate() ===
              date.getDate() &&
            analyzed.getMonth() ===
              date.getMonth() &&
            analyzed.getFullYear() ===
              date.getFullYear()
          );
        });

      let high = 0;
      let medium = 0;
      let low = 0;

      dayCases.forEach((item) => {
        (
          item?.highlights || []
        ).forEach((h) => {
          if (h?.level === "high") {
            high += 1;
          } else if (
            h?.level === "low"
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
        .replace(
          /[<>]/g,
          ""
        )
    : null;
}


function getTopSenderDomains(
  cases,
  limit = 5
) {
  const counts = new Map();

  cases.forEach((item) => {
    const domain =
      extractDomain(item);

    if (!domain) return;

    counts.set(
      domain,
      (counts.get(domain) || 0) + 1
    );
  });

  return [
    ...counts.entries(),
  ]
    .sort(
      (a, b) => b[1] - a[1]
    )
    .slice(0, limit)
    .map(
      ([domain, count]) => ({
        domain,
        count,
      })
    );
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
    analyze,
    isLoading: isAnalyzing,
    error: analyzeError,
  } = useAnalyzeEmail();

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
     ANALYZE EMAIL
     ======================================================= */

  async function handleFileSelected(
    file
  ) {
    const result =
      await analyze(file).catch(
        () => null
      );

    if (result) {
      setCurrentCase(result);
      refetch();
    }
  }


  /* =======================================================
     CASE DATA
     ======================================================= */

  const cases = Array.isArray(
    fetchedCases
  )
    ? fetchedCases
    : [];


  /* =======================================================
     GMAIL MERGE DATA (computed first so CHART DATA below
     can fold it straight into the existing widgets)
     ======================================================= */

  const mailboxStats =
    gmailDashboard?.stats || {};

  // Weekday -> mailbox email count, used only as a fallback
  // series for the Alert Volume chart when there's no case
  // activity yet, so that chart shows real numbers instead
  // of a placeholder.
  const mailboxActivityByWeekday = useMemo(
    () =>
      getMailboxActivityByWeekday(
        gmailConnected
          ? gmailDashboard?.activity
          : []
      ),
    [gmailConnected, gmailDashboard]
  );


  /* =======================================================
     CHART DATA
     ======================================================= */

  const chartData = useMemo(
    () =>
      getChartData(cases).map((day) => ({
        ...day,
        mailboxTotal:
          mailboxActivityByWeekday.get(
            day.label
          ) || 0,
      })),
    [cases, mailboxActivityByWeekday]
  );

  const breakdownData = useMemo(
    () =>
      getDailyBreakdown(cases),
    [cases]
  );

  const authBreakdown = useMemo(
    () =>
      getAuthBreakdown(cases),
    [cases]
  );

  const highlightTrend = useMemo(
    () =>
      getHighlightTrend(cases),
    [cases]
  );

  const caseTopDomains = useMemo(
    () =>
      getTopSenderDomains(cases),
    [cases]
  );

  // Fold Gmail's own top-domain counts into the SAME
  // "Top Sender Domains" list the cases already populate,
  // rather than rendering a second list for mailbox data.
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
     STATISTICS
     ======================================================= */

  const totalFlags =
    cases.reduce(
      (sum, item) =>
        sum +
        (
          item?.highlights
            ?.length || 0
        ),
      0
    );


  const todayCount =
    cases.filter(
      (item) =>
        isToday(
          item?.analyzedAt
        )
    ).length;


  const highRiskCount =
    cases.filter(
      (item) =>
        item?.severity === "red" ||
        Number(
          item?.riskScore || 0
        ) >= 80
    ).length;


  const reviewedCount =
    cases.filter(
      (item) =>
        item?.reviewed === true
    ).length;


  const averageScore =
    cases.length
      ? Math.round(
          cases.reduce(
            (sum, item) =>
              sum +
              Number(
                item?.riskScore || 0
              ),
            0
          ) / cases.length
        )
      : 0;


  const totalAlerts =
    chartData.reduce(
      (sum, item) =>
        sum +
        item.total,
      0
    );


  /* =======================================================
     GMAIL MERGE — fold mailbox numbers into the SAME stat
     cards instead of a separate stat row. Case data always
     wins when it exists; mailbox numbers only fill in the
     gaps (and annotate the delta) when it doesn't.
     ======================================================= */

  const mailboxToday = gmailConnected
    ? Number(mailboxStats.today || 0)
    : 0;

  const mailboxThisWeek = gmailConnected
    ? Number(mailboxStats.thisWeek || 0)
    : 0;

  const mailboxTotalFetched = gmailConnected
    ? Number(mailboxStats.totalFetched || 0)
    : 0;

  const mailboxUnread = gmailConnected
    ? Number(mailboxStats.unread || 0)
    : 0;

  const mergedTodayCount =
    todayCount || totalAlerts || mailboxToday;

  const mergedReviewedCount =
    reviewedCount ||
    cases.length ||
    mailboxTotalFetched;

  const todayDelta = !todayCount && gmailConnected
    ? `${mailboxThisWeek} mailbox this wk`
    : null;

  const reviewedDelta = !reviewedCount && gmailConnected
    ? `${mailboxUnread} unread`
    : null;


  /* =======================================================
     RECENT CASES
     ======================================================= */

  const recentCases = [
    ...cases,
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
          currentCase={currentCase}
          setCurrentCase={
            setCurrentCase
          }

          handleFileSelected={
            handleFileSelected
          }

          isAnalyzing={
            isAnalyzing
          }

          analyzeError={
            analyzeError
          }

          navigate={navigate}

          cases={cases}

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

          todayDelta={todayDelta}

          highRiskCount={
            highRiskCount
          }

          reviewedCount={
            mergedReviewedCount
          }

          reviewedDelta={reviewedDelta}

          averageScore={
            averageScore
          }

          totalAlerts={
            totalAlerts
          }

          gmailStatus={gmailStatus}
          gmailConnected={gmailConnected}
          gmailSyncing={gmailSyncing}
          gmailLoadProgress={gmailLoadProgress}
          gmailError={gmailError}
          onSyncGmail={syncGmailNow}

          recentCases={
            recentCases
          }
        />

      </div>
    </main>
  );
}
