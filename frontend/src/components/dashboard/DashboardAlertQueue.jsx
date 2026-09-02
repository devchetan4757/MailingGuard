import { useMemo, useState } from "react";
import { DashboardPanel } from "./DashboardWidgets";
import { Search } from "lucide-react";

export default function DashboardAlertQueue({
  recentCases,
  totalAlerts,
  navigate,
}) {
  const [search, setSearch] = useState("");

  const filteredCases = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) return recentCases;

    return recentCases.filter((item) => {
      const id = String(item?.id || item?.caseId || "");
      const sender = String(item?.sender || item?.from || "");
      const subject = String(item?.subject || item?.title || "");

      return (
        id.toLowerCase().includes(query) ||
        sender.toLowerCase().includes(query) ||
        subject.toLowerCase().includes(query)
      );
    });
  }, [recentCases, search]);

  return (
    <DashboardPanel
      title={
        <>
          <span>Alert Queue</span>
          <small> (Today)</small>
        </>
      }
      className="ref-queue-panel"
      right={
        <div className="ref-table-search">
          <Search size={15} />

          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search sender, subject, ID…"
            aria-label="Search alert queue"
          />
        </div>
      }
    >
      <div className="ref-table-wrap">
        <table className="ref-alert-table">
          <thead>
            <tr>
              <th>Message ID</th>
              <th>Sender</th>
              <th>Subject</th>
              <th>Timestamp</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>

          <tbody>
            {filteredCases.length > 0 ? (
              filteredCases.map((item, index) => {
                const status =
                  item?.severity === "red"
                    ? "Open"
                    : item?.reviewed
                      ? "Resolved"
                      : "Pending";

                const id =
                  item?.id ||
                  item?.caseId ||
                  `NA${String(index + 32000669)}`;

                return (
                  <tr key={id}>
                    <td>{id}</td>

                    <td>
                      {item?.sender ||
                        item?.from ||
                        "Unknown sender"}
                    </td>

                    <td>
                      {item?.subject ||
                        item?.title ||
                        "Suspicious email"}
                    </td>

                    <td>
                      {item?.analyzedAt
                        ? new Date(
                            item.analyzedAt
                          ).toLocaleString([], {
                            month: "short",
                            day: "numeric",
                            hour: "numeric",
                            minute: "2-digit",
                          })
                        : "Unknown"}
                    </td>

                    <td>
                      <span
                        className={`ref-status ref-status-${status.toLowerCase()}`}
                      >
                        {status}
                      </span>
                    </td>

                    <td>
                      <button
                        type="button"
                        className="ref-view"
                        onClick={() =>
                          navigate(
                            `/results/${id}`
                          )
                        }
                      >
                        View
                      </button>
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td
                  colSpan="6"
                  className="ref-empty"
                >
                  {search.trim()
                    ? "No alerts match your search."
                    : "No email alerts found."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="ref-queue-footer">
        <span>
          {search.trim()
            ? `${filteredCases.length} of ${totalAlerts || recentCases.length} alerts match “${search.trim()}”`
            : `${totalAlerts || recentCases.length} alerts shown from current analysis data`}
        </span>

        <button
          type="button"
          onClick={() =>
            navigate("/reports")
          }
        >
          View all alerts →
        </button>
      </div>
    </DashboardPanel>
  );
}
