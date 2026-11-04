export function Page() {
  return (
    <main>
      <h2>Here you can manage how and when you receive notifications</h2>
      <p>This dashboard shows how tickets move through each stage so that you can spot bottlenecks early.</p>
      <Button onClick={save}>Yes</Button>
      <input placeholder="Simply type a name" />
      <a href="/older">Click here to see older messages</a>
    </main>
  );
}
const empty = "It looks like this folder is empty. Files you upload will appear here, sorted by date.";
