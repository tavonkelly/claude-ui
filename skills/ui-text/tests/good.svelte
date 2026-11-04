<script>
  let count = 0;
  const label = count === 1 ? 'file' : 'files';
</script>
<h2>Uploads</h2>
{#if count === 0}
  <p>No uploads yet</p>
  <button on:click={pick}>Choose files</button>
{:else}
  <p>{count} {label}</p>
{/if}
