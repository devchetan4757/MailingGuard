/**
 * Epic 1 owner.
 * PROPS CONTRACT: { onFileSelected: (file: File) => void, isLoading: boolean }
 * This is the only element competing for attention on the upload page
 * (see UI structure PDF, page 2) - keep it that way.
 */

export default function UploadBox({ onFileSelected, isLoading }) {
  function handleChange(e) {
    const file = e.target.files?.[0];
    if (file) onFileSelected(file);
  }

  function handleDrop(e) {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) onFileSelected(file);
  }

  return (
    <label
      onDrop={handleDrop}
      onDragOver={(e) => e.preventDefault()}
      className="border-2 border-dashed border-graphite/30 rounded-sm h-44 flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-brass transition-colors"
    >
      <input type="file" accept=".eml" className="hidden" onChange={handleChange} disabled={isLoading} />
      <span className="text-sm text-graphite">
        {isLoading ? "Analyzing…" : "Drag a .eml file here, or click to browse"}
      </span>
      <span className="text-xs text-graphite/50">Accepted: .eml · max 2MB</span>
    </label>
  );
}
