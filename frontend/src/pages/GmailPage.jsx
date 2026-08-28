import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Inbox,
  Mail,
  MailOpen,
  RefreshCw,
  Search,
  ShieldCheck,
  Unplug,
  X,
} from "lucide-react";

import { connectGmail } from "../api/gmailApi";
import { useGmailOverview } from "../hooks/useGmailOverview";
import GmailIcon from "../components/gmail/GmailIcon";

import "../styles/gmail.css";

const MAIL_PAGE_SIZE = 10;


/* =========================================================
   HELPERS
   ========================================================= */

function parseSender(raw) {
  if (!raw) {
    return { name: "Unknown sender", email: "" };
  }

  const match = raw.match(/^"?([^"<]*)"?\s*<([^>]+)>$/);

  if (match) {
    const name = match[1].trim();
    const email = match[2].trim();
    return { name: name || email, email };
  }

  return { name: raw, email: raw };
}

function formatMailDate(raw) {
  if (!raw) return "";

  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return "";

  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();

  return sameDay
    ? date.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    : date.toLocaleDateString([], {
        month: "short",
        day: "numeric",
      });
}

function initialsFrom(name) {
  const trimmed = (name || "").trim();
  if (!trimmed) return "?";

  return trimmed
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function isSameDay(a, b) {
  return (
    a.getDate() === b.getDate() &&
    a.getMonth() === b.getMonth() &&
    a.getFullYear() === b.getFullYear()
  );
}

function isToday(raw) {
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return false;
  return isSameDay(date, new Date());
}

function isThisWeek(raw) {
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return false;

  const now = new Date();
  const weekAgo = new Date(now);
  weekAgo.setDate(now.getDate() - 7);

  return date >= weekAgo && date <= now;
}

const MAIL_FILTERS = [
  { id: "all", label: "All" },
  { id: "unread", label: "Unread" },
  { id: "today", label: "Today" },
  { id: "week", label: "This week" },
];

function accountDisplayName(email) {
  if (!email) return "Gmail Account";

  const local = email.split("@")[0];

  return local
    .replace(/[._-]+/g, " ")
    .split(" ")
    .filter(Boolean)
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}


/* =========================================================
   PAGE
   ========================================================= */

export default function GmailPage() {
  const [connecting, setConnecting] = useState(false);
  const [mailPage, setMailPage] = useState(1);
  const [mailSearch, setMailSearch] = useState("");
  const [mailFilter, setMailFilter] = useState("all");
  const [oauthError, setOauthError] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();

  const {
    status,
    dashboard,
    connected,
    isLoading,
    isSyncing,
    loadProgress,
    error,
    sync,
    refetch,
  } = useGmailOverview();

  // Google redirects the browser straight back here after OAuth
  // (via the backend's /callback -> /gmail redirect), so pick up
  // the connect/error result from the URL, refresh the Gmail
  // data, and clean the query string.
  useEffect(() => {
    const connectedParam = searchParams.get("gmail_connected");
    const errorParam = searchParams.get("gmail_error");

    if (!connectedParam && !errorParam) return;

    if (errorParam) {
      setOauthError(errorParam);
    } else {
      setOauthError(null);
      refetch();
    }

    setSearchParams(
      (params) => {
        params.delete("gmail_connected");
        params.delete("gmail_error");
        return params;
      },
      { replace: true }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  async function handleConnect() {
    try {
      setConnecting(true);
      await connectGmail();
    } catch {
      setConnecting(false);
    }
  }

  async function handleSync() {
    setMailPage(1);
    await sync();
  }

  const email = status?.profile?.email || "";
  const profilePicture = status?.profile?.picture || "";
  const accountName = status?.profile?.name || accountDisplayName(email);

  const stats = dashboard?.stats || {};
  const messages = dashboard?.messages || [];

  const filteredMessages = useMemo(() => {
    const query = mailSearch.trim().toLowerCase();

    return messages.filter((message) => {
      if (mailFilter === "unread") {
        if (!(message.labelIds || []).includes("UNREAD")) return false;
      } else if (mailFilter === "today") {
        if (!isToday(message.date)) return false;
      } else if (mailFilter === "week") {
        if (!isThisWeek(message.date)) return false;
      }

      if (!query) return true;

      const sender = parseSender(message.from);
      const haystack = [
        sender.name,
        sender.email,
        message.subject,
        message.snippet,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return haystack.includes(query);
    });
  }, [messages, mailSearch, mailFilter]);

  function handleMailSearchChange(value) {
    setMailSearch(value);
    setMailPage(1);
  }

  function handleMailFilterChange(filterId) {
    setMailFilter(filterId);
    setMailPage(1);
  }

  const mailTotalPages = Math.max(
    1,
    Math.ceil(filteredMessages.length / MAIL_PAGE_SIZE)
  );

  const mailCurrentPage = Math.min(
    mailPage,
    mailTotalPages
  );

  const mailPageStart =
    (mailCurrentPage - 1) * MAIL_PAGE_SIZE;

  const pagedMessages = filteredMessages.slice(
    mailPageStart,
    mailPageStart + MAIL_PAGE_SIZE
  );

  const progressPct = loadProgress
    ? Math.min(
        100,
        Math.round(
          (loadProgress.loaded /
            Math.max(loadProgress.total, 1)) *
            100
        )
      )
    : null;

  const cacheAgeMinutes = dashboard?.cacheAgeSeconds
    ? Math.max(1, Math.round(dashboard.cacheAgeSeconds / 60))
    : 0;

  const profileStateLabel = loadProgress
    ? `Loading ${loadProgress.loaded}/${loadProgress.total}…`
    : dashboard?.cached
      ? `Synced · cache ${cacheAgeMinutes}m ago`
      : dashboard
        ? "Synced just now"
        : "Checking mailbox…";


  /* =======================================================
     INITIAL LOADING (before we even know connection status)
     ======================================================= */

  if (isLoading && !status) {
    return (
      <main className="gmail-page">
        <div className="gmail-page-shell">
          <div className="gmail-page-loading">
            Loading Gmail integration...
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="gmail-page">
      <div className="gmail-page-shell">

        {/* =================================================
            PAGE HEADER
            ================================================= */}

        <header className="gmail-page-header">
          <div>
            <span className="gmail-eyebrow">
              INTEGRATION
            </span>

            <h1>
              <GmailIcon size={26} className="gmail-title-icon" />
              Gmail
            </h1>

            <p>
              Connect and manage the Gmail
              mailbox used by MailingGuard.
            </p>
          </div>

          <div
            className={`gmail-connection-badge ${
              connected ? "is-connected" : ""
            }`}
          >
            {connected ? (
              <>
                <CheckCircle2 size={15} />
                Connected
              </>
            ) : (
              <>
                <Unplug size={15} />
                Not connected
              </>
            )}
          </div>
        </header>

        {oauthError && (
          <div className="gmail-page-error">
            {oauthError}
          </div>
        )}

        {error && (
          <div className="gmail-page-error">
            {error}
          </div>
        )}

        {connected && status?.needsReconnectForProfile && (
          <div className="gmail-page-notice">
            <ShieldCheck size={14} />
            Your profile photo isn't available yet — reconnect
            your Gmail account once to grant access to it.
            <button
              type="button"
              className="gmail-page-notice-action"
              onClick={handleConnect}
              disabled={connecting}
            >
              {connecting ? "Reconnecting…" : "Reconnect"}
            </button>
          </div>
        )}

        {/* =================================================
            CONNECTION CARD
            ================================================= */}

        {!connected ? (
          <section className="gmail-integration-card">
            <div className="gmail-integration-icon">
              <GmailIcon size={26} />
            </div>

            <div className="gmail-integration-content">
              <span className="gmail-panel-kicker">
                GOOGLE ACCOUNT
              </span>

              <h2>
                Connect your Gmail account
              </h2>

              <p>
                Sign in with the Gmail account
                you want MailingGuard to use
                for mailbox overview data.
              </p>

              <div className="gmail-permission-note">
                <ShieldCheck size={16} />

                <span>
                  MailingGuard currently requests
                  <strong>
                    {" "}read-only Gmail access
                  </strong>
                  .
                </span>
              </div>

              <button
                type="button"
                className="gmail-google-button"
                onClick={handleConnect}
                disabled={connecting}
              >
                {connecting ? (
                  <>
                    <RefreshCw
                      size={16}
                      className="gmail-spin"
                    />
                    Connecting...
                  </>
                ) : (
                  <>
                    <GmailIcon size={16} />
                    Connect with Google
                    <ExternalLink
                      size={15}
                    />
                  </>
                )}
              </button>
            </div>
          </section>
        ) : (
          <section className="gmail-overview">

            {/* =============================================
                ACCOUNT / PROFILE STRIP
                ============================================= */}

            <div className="gmail-profile-strip">
              <div className="gmail-avatar">
                {profilePicture ? (
                  <img
                    src={profilePicture}
                    alt={accountName}
                    referrerPolicy="no-referrer"
                  />
                ) : (
                  <GmailIcon size={22} />
                )}
              </div>

              <div className="gmail-profile-copy">
                <strong>
                  {accountName}
                </strong>

                <span>
                  {email || "Authenticated Gmail mailbox"}
                </span>
              </div>

              <span className="gmail-profile-state">
                <span
                  className="gmail-status-dot"
                  aria-hidden="true"
                />
                {profileStateLabel}
              </span>

              <div className="gmail-head-actions">
                <span className="gmail-cache-pill">
                  Cache · 10 min
                </span>

                <button
                  type="button"
                  className="gmail-sync-button"
                  onClick={handleSync}
                  disabled={isSyncing || Boolean(loadProgress)}
                >
                  <RefreshCw
                    size={14}
                    className={
                      isSyncing || loadProgress
                        ? "gmail-spin"
                        : ""
                    }
                  />
                  {isSyncing ? "Syncing..." : "Sync"}
                </button>
              </div>
            </div>

            {progressPct !== null && (
              <div
                className="gmail-progress-bar"
                role="progressbar"
                aria-valuenow={progressPct}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <div
                  className="gmail-progress-bar-fill"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
            )}

            {/* =============================================
                STAT ROW
                ============================================= */}

            <div className="gmail-stat-grid">
              <StatTile
                icon={<Inbox size={16} />}
                label="Fetched"
                value={stats.totalFetched ?? 0}
                loading={!dashboard}
              />

              <StatTile
                icon={<Mail size={16} />}
                label="Today"
                value={stats.today ?? 0}
                loading={!dashboard}
              />

              <StatTile
                icon={<RefreshCw size={16} />}
                label="This week"
                value={stats.thisWeek ?? 0}
                loading={!dashboard}
              />

              <StatTile
                icon={<MailOpen size={16} />}
                label="Unread"
                value={stats.unread ?? 0}
                loading={!dashboard}
              />
            </div>

            {/* =============================================
                LOADED MAIL LIST
                ============================================= */}

            <div className="gmail-panel">
              <div className="gmail-panel-head">
                <div>
                  <span className="gmail-panel-kicker">
                    MAILBOX
                  </span>

                  <h3>
                    Recently loaded mail
                  </h3>
                </div>

                <span className="gmail-panel-count">
                  {filteredMessages.length}
                  {filteredMessages.length !== messages.length
                    ? ` of ${messages.length} loaded`
                    : " loaded"}
                  {stats.totalFetched
                    ? ` · ${stats.totalFetched} total`
                    : ""}
                </span>
              </div>

              {dashboard && messages.length > 0 && (
                <div className="gmail-mail-toolbar">
                  <div className="gmail-search">
                    <Search size={14} />

                    <input
                      type="text"
                      value={mailSearch}
                      placeholder="Search sender, subject, snippet…"
                      onChange={(event) =>
                        handleMailSearchChange(event.target.value)
                      }
                    />

                    {mailSearch && (
                      <button
                        type="button"
                        className="gmail-search-clear"
                        aria-label="Clear search"
                        onClick={() => handleMailSearchChange("")}
                      >
                        <X size={13} />
                      </button>
                    )}
                  </div>

                  <div className="gmail-filter-chips">
                    {MAIL_FILTERS.map((filter) => (
                      <button
                        key={filter.id}
                        type="button"
                        className={`gmail-filter-chip ${
                          mailFilter === filter.id ? "is-active" : ""
                        }`}
                        onClick={() =>
                          handleMailFilterChange(filter.id)
                        }
                      >
                        {filter.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {!dashboard ? (
                <div className="gmail-list-empty">
                  Loading messages…
                </div>
              ) : messages.length === 0 ? (
                <div className="gmail-list-empty">
                  No messages loaded yet.
                </div>
              ) : filteredMessages.length === 0 ? (
                <div className="gmail-list-empty">
                  No messages match your search or filter.
                </div>
              ) : (
                <>
                  <div className="gmail-mail-list">
                    {pagedMessages.map((message) => {
                      const sender = parseSender(
                        message.from
                      );

                      const isUnread = (
                        message.labelIds || []
                      ).includes("UNREAD");

                      return (
                        <div
                          key={message.id}
                          className={`gmail-mail-row ${
                            isUnread ? "is-unread" : ""
                          }`}
                        >
                          <div className="gmail-mail-avatar">
                            {initialsFrom(sender.name)}
                          </div>

                          <div className="gmail-mail-body">
                            <span className="gmail-mail-sender">
                              {sender.name}
                            </span>

                            <span className="gmail-mail-subject">
                              {message.subject ||
                                "(no subject)"}
                            </span>

                            {message.snippet && (
                              <span className="gmail-mail-snippet">
                                {message.snippet}
                              </span>
                            )}
                          </div>

                          <div className="gmail-mail-meta">
                            {isUnread && (
                              <span
                                className="gmail-mail-unread-dot"
                                aria-label="Unread"
                              />
                            )}

                            <span className="gmail-mail-date">
                              {formatMailDate(message.date)}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {mailTotalPages > 1 && (
                    <div className="gmail-mail-pagination">
                      <button
                        type="button"
                        className="gmail-page-button"
                        onClick={() =>
                          setMailPage((page) =>
                            Math.max(1, page - 1)
                          )
                        }
                        disabled={mailCurrentPage <= 1}
                        aria-label="Previous page"
                      >
                        <ChevronLeft size={14} />
                      </button>

                      <span className="gmail-page-status">
                        Page {mailCurrentPage} of{" "}
                        {mailTotalPages}
                      </span>

                      <button
                        type="button"
                        className="gmail-page-button"
                        onClick={() =>
                          setMailPage((page) =>
                            Math.min(
                              mailTotalPages,
                              page + 1
                            )
                          )
                        }
                        disabled={
                          mailCurrentPage >= mailTotalPages
                        }
                        aria-label="Next page"
                      >
                        <ChevronRight size={14} />
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          </section>
        )}

        {/* =================================================
            INFO
            ================================================= */}

        <section className="gmail-info-grid">

          <div className="gmail-info-card">
            <ShieldCheck size={18} />

            <div>
              <h3>
                Read-only access
              </h3>

              <p>
                The current integration only
                reads mailbox information required
                for the dashboard.
              </p>
            </div>
          </div>

          <div className="gmail-info-card">
            <RefreshCw size={18} />

            <div>
              <h3>
                Cached for 10 minutes
              </h3>

              <p>
                Dashboard requests reuse cached
                Gmail data instead of repeatedly
                requesting the Gmail API.
              </p>
            </div>
          </div>

        </section>

      </div>
    </main>
  );
}


/* =========================================================
   STAT TILE
   ========================================================= */

function StatTile({ icon, label, value, loading }) {
  return (
    <div className="gmail-stat">
      <span className="gmail-stat-icon">
        {icon}
      </span>

      <div>
        <span>{label}</span>
        <strong>{loading ? "…" : value}</strong>
      </div>
    </div>
  );
}
