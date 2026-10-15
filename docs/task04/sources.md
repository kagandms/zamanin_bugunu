# Resmî kaynak doğrulaması — 15 Ekim 2026

- [Cloudflare Cron Triggers](https://developers.cloudflare.com/workers/configuration/cron-triggers/): UTC cron, scheduled handler, config crons, değişiklik yayılımı15dk'ya kadar.
- [Scheduled handler](https://developers.cloudflare.com/workers/runtime-apis/handlers/scheduled/): controller.scheduledTime epoch milisaniye, controller.cron; gerçek Date.now ayrı tutuldu.
- [Cloudflare secrets](https://developers.cloudflare.com/workers/configuration/secrets/): secret binding; plaintext vars içine credential yok.
- [GitHub workflow dispatch REST](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event): filenameworkflowid, ref, configuredinputs; fine-grained Actionswrite; güncel2026-03-10 API200 workflow_run_id/run_url/html_url. Güncel parametre listesinde return_run_details yok: gönderilmedi. Eski204 yanıtı toleransla kabul edilir;200 ayrıntısı eksikse kabul+runIDunknown.
- [Workflow runs REST](https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-workflow): Actionsread/publicanonymous, event/branch ve100perpage. Observer tekboundedpage; hiçrunbulamamak kesindispatchbaşarısızlığı değildir.
- [GitHub concurrency](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency): queue:max en fazla100pending, cancel-in-progress:true ile birleştirilemez. Var olan ortak group/queue korunur.
- [Workers pricing](https://developers.cloudflare.com/workers/platform/pricing/): Free100krequest/gün10msCPU, Paidbaşlangıç$5 ve account genel aşım. Nominal hacim ve duplicate sınırları operations.md'de.
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions): standart GitHubhosted publicrepo çalışma ile private/largerunner ücret politikaları ayrıdır. Bu görev hesapfaturası okumadı.
- Sürümler [resmî npm registry Wrangler](https://registry.npmjs.org/wrangler/latest) ve [TypeScript](https://registry.npmjs.org/typescript/latest) üzerinden `npm view` ile doğrulandı: Wrangler4.151.0, TypeScript7.0.2. Tam dependency ağacı/integrity package-lock.json içinde; npm audit install sırasında0vulnerability bildirdi.

Yerel test/dry-run, bu API'lere gerçek POST veya canlı external cron doğrulaması değildir.
