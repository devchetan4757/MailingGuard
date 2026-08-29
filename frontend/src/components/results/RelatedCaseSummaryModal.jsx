/**
 * Epic 3 owner.
 * PROPS CONTRACT: { caseId: string | null, onClose: () => void }
 * Opens as a side panel/modal without leaving the current results page
 * (master doc, section 6, page flow).
 * TODO (Epic 3): fetch the related case's summary via casesApi.getCase(caseId)
 * and render it here instead of the placeholder text.
 */

import Modal from "../shared/Modal";

export default function RelatedCaseSummaryModal({ caseId, onClose }) {
  return (
    <Modal isOpen={!!caseId} onClose={onClose}>
      <p className="font-serif text-lg">Case #{caseId}</p>
      <p className="text-sm text-graphite/60 mt-2">TODO: load and show this case's summary.</p>
    </Modal>
  );
}
