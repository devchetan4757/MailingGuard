/**
 * Epic 4 owner.
 * PROPS CONTRACT: { caseId: string }
 * Downloads the case file, no navigation on click.
 */

import { getCaseReportUrl } from "../../api/casesApi";

export default function DownloadReportButton({ caseId }) {
  return (
    <a
      href={getCaseReportUrl(caseId)}
      className="inline-block text-sm border border-graphite/30 rounded-sm px-4 py-2"
      download
    >
      ⬇ Download case file (PDF)
    </a>
  );
}
