import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  RefreshCw,
  Search,
  ShieldCheck,
  Unplug,
  X,
} from "lucide-react";

import { connectGmail } from "../api/gmailApi";
import { useGmailOverview } from "../hooks/useGmailOverview";
import { useAnalyzeGmailMessage } from "../hooks/useAnalyzeGmailMessage";
import { useGmailMessageContent } from "../hooks/useGmailMessageContent";
import { useCaseContext } from "../context/CaseContext";
import { useCases } from "../hooks/useCases";
import GmailIcon from "../components/gmail/GmailIcon";
import MailHandoffMenu from "../components/gmail/MailHandoffMenu";
import MailReaderModal from "../components/gmail/MailReaderModal";

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

// Personal/free-mail providers where a domain logo would just be the
// provider's own brand (Gmail's "G", Outlook's "O"...) rather than
// anything that identifies the actual sender — skip the logo lookup
// for these and fall back straight to initials.
const PERSONAL_EMAIL_DOMAINS = new Set([
  "gmail.com",
  "googlemail.com",
  "yahoo.com",
  "ymail.com",
  "outlook.com",
  "hotmail.com",
  "live.com",
  "msn.com",
  "icloud.com",
  "me.com",
  "mac.com",
  "aol.com",
  "protonmail.com",
  "proton.me",
  "zoho.com",
  "gmx.com",
  "yandex.com",
]);

function senderDomain(email) {
  if (!email || !email.includes("@")) return null;
  return email.split("@")[1].trim().toLowerCase();
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
  const navigate = useNavigate();
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

  const { setCurrentCase } = useCaseContext();
  const { refetch: refetchCases } = useCases();

  const {
    analyze: analyzeMessage,
    pendingId: handoffPendingId,
    error: handoffError,
  } = useAnalyzeGmailMessage();

  const [readerMailId, setReaderMailId] = useState(null);
  const {
    message: readerMessage,
    isLoading: isReaderLoading,
    error: readerError,
    open: openReader,
    close: closeReaderContent,
  } = useGmailMessageContent();

  function handleOpenMail(messageId) {
    setReaderMailId(messageId);
    openReader(messageId).catch(() => {});
  }

  function handleCloseReader() {
    setReaderMailId(null);
    closeReaderContent();
  }

  // Hand a single loaded message over to the analysis pipeline, then
  // jump straight to whichever surface the user picked — the AI Deep
  // Analysis page and the Origin Analysis page both just read the
  // same `currentCase`, so one analyze call feeds either.
  async function handleHandoff(messageId, targetId) {
    const result = await analyzeMessage(messageId).catch(() => null);

    if (!result) return;

    setCurrentCase(result);
    refetchCases();
    navigate(targetId === "origin" ? "/origin" : "/analyze");
  }

  // Reached from the reader modal's own "AI Deep Analysis" /
  // "Origin Analysis" buttons — close the reader first so it isn't
  // left open underneath the page we navigate to.
  function handleHandoffFromReader(targetId) {
    const messageId = readerMailId;
    handleCloseReader();
    if (messageId) handleHandoff(messageId, targetId);
  }

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
                tone="cyan"
                label="Loaded"
                value={stats.totalFetched ?? 0}
                loading={!dashboard}
                title="Messages MailingGuard has pulled from Gmail into its cache"
              />

              <StatTile
                tone="blue"
                label="Today"
                value={stats.today ?? 0}
                loading={!dashboard}
              />

              <StatTile
                tone="violet"
                label="This week"
                value={stats.thisWeek ?? 0}
                loading={!dashboard}
              />

              <StatTile
                tone="amber"
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
                  {filteredMessages.length !== messages.length
                    ? `${filteredMessages.length} of ${messages.length} match`
                    : `${messages.length} shown`}
                  {stats.totalFetched > messages.length
                    ? ` · ${stats.totalFetched} fetched from Gmail`
                    : ""}
                </span>
              </div>

              {handoffError && (
                <div className="gmail-handoff-error">
                  <AlertTriangle size={13} />
                  Couldn't hand that email over: {handoffError}
                </div>
              )}

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
                          className={`gmail-mail-row gmail-mail-row--clickable ${
                            isUnread ? "is-unread" : ""
                          }`}
                          role="button"
                          tabIndex={0}
                          onClick={() => handleOpenMail(message.id)}
                          onKeyDown={(event) => {
                            if (event.key === "Enter" || event.key === " ") {
                              event.preventDefault();
                              handleOpenMail(message.id);
                            }
                          }}
                        >
                          <div className="gmail-mail-avatar-wrap">
                            <SenderAvatar name={sender.name} email={sender.email} />
                            {isUnread && (
                              <span
                                className="gmail-mail-unread-dot"
                                aria-hidden="true"
                              />
                            )}
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
                            <span className="gmail-mail-date">
                              {formatMailDate(message.date)}
                            </span>

                            <MailHandoffMenu
                              isBusy={handoffPendingId === message.id}
                              onSelect={(targetId) =>
                                handleHandoff(message.id, targetId)
                              }
                            />
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
            FOOTNOTE
            ================================================= */}

        <section className="gmail-footnote">
          <span className="gmail-footnote-item">
            <ShieldCheck size={13} />
            Read-only Gmail access — MailingGuard only reads what it
            needs for the dashboard and analysis; it never sends,
            deletes, or modifies mail.
          </span>

          {connected && (
            <span className="gmail-footnote-item">
              <RefreshCw size={13} />
              Mailbox data is cached locally for 10 minutes between
              syncs, so the numbers above may lag a live Gmail
              inbox slightly — hit Sync for the latest.
            </span>
          )}
        </section>

      </div>

      <MailReaderModal
        isOpen={Boolean(readerMailId)}
        message={readerMessage}
        isLoading={isReaderLoading}
        error={readerError}
        onClose={handleCloseReader}
        onHandoff={handleHandoffFromReader}
      />
    </main>
  );
}


/* =========================================================
   STAT TILE
   ========================================================= */

function StatTile({ label, value, loading, title, tone = "cyan" }) {
  return (
    <div className={`gmail-stat gmail-stat--${tone}`} title={title}>
      <div className="gmail-stat-copy">
        <span>{label}</span>
        <strong>{loading ? "…" : value}</strong>
      </div>
    </div>
  );
}


/* =========================================================
   SENDER AVATAR
   Shows the sending organization's public logo when the
   sender's domain has one (e.g. a company or vendor mail),
   and falls back to the plain initials circle for personal
   addresses or when no logo can be found.
   ========================================================= */

function SenderAvatar({ name, email }) {
  const [imgFailed, setImgFailed] = useState(false);

  const domain = senderDomain(email);
  const canTryLogo = Boolean(domain) && !PERSONAL_EMAIL_DOMAINS.has(domain);
  const showImage = canTryLogo && !imgFailed;

  return (
    <div className="gmail-mail-avatar">
      {showImage ? (
        <img
          src={`https://www.google.com/s2/favicons?domain=${domain}&sz=64`}
          alt=""
          loading="lazy"
          onError={() => setImgFailed(true)}
        />
      ) : (
        <span>{initialsFrom(name)}</span>
      )}
    </div>
  );
}
