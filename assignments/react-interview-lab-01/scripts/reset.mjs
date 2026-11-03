try {
  const response = await fetch("http://127.0.0.1:4173/api/__dev/reset", {
    method: "POST",
  });
  if (!response.ok) throw new Error(`Reset failed (${response.status})`);
  console.log("Fixtures restored. Reload the browser to clear local results.");
} catch (error) {
  console.error(error.message, "Start npm run dev first.");
  process.exitCode = 1;
}
