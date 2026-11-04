// Renders the file list. You can pass an empty array; this comment is not UI text.
export function Files({ items }: Props) {
  const label = items.length > 0 ? `${items.length} selected` : 'None selected';
  return (
    <section>
      <h2>Files</h2>
      <Button variant="primary" onClick={upload}>Upload files</Button>
      {items.length === 0 && <p className="empty">No files</p>}
      <IconButton aria-label="Delete file" icon={<TrashIcon />} />
      <span title="Last modified">2 min ago</span>
    </section>
  );
}
