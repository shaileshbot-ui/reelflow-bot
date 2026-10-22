export default {
  async scheduled(event, env, ctx) { ctx.waitUntil(triggerGitHub(env)); },
  async fetch(request, env) {
    if (request.method !== "POST") return new Response("ReelFlow cron worker is running.",{status:200});
    if (!env.MANUAL_TRIGGER_SECRET || request.headers.get("x-trigger-secret") !== env.MANUAL_TRIGGER_SECRET)
      return new Response("Unauthorized",{status:401});
    await triggerGitHub(env);
    return new Response("GitHub Actions workflow dispatched.",{status:202});
  }
};
async function triggerGitHub(env) {
  if (!env.GH_OWNER || !env.GH_REPO || !env.GH_TOKEN) throw new Error("Missing GH_OWNER/GH_REPO/GH_TOKEN");
  const workflow=env.GH_WORKFLOW || "daily-reels.yml";
  const url=`https://api.github.com/repos/${env.GH_OWNER}/${env.GH_REPO}/actions/workflows/${workflow}/dispatches`;
  const r=await fetch(url,{method:"POST",headers:{
    "Authorization":`Bearer ${env.GH_TOKEN}`,"Accept":"application/vnd.github+json",
    "X-GitHub-Api-Version":"2022-11-28","User-Agent":"ReelFlow-Cron"
  },body:JSON.stringify({ref:"main"})});
  if(!r.ok) throw new Error(`GitHub dispatch failed: ${r.status} ${await r.text()}`);
}
