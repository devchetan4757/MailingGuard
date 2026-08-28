import { DashboardPanel } from "./DashboardWidgets";
import { Search } from "lucide-react";

export default function DashboardAlertQueue({
  recentCases,
  totalAlerts,
  navigate,
}) {
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
          <span>Search</span>
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
            {recentCases.length > 0 ? (
              recentCases.map((item, index) => {
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
                  No email alerts found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="ref-queue-footer">
        <span>
          {totalAlerts ||
            recentCases.length}{" "}
          alerts shown from current
          analysis data
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
