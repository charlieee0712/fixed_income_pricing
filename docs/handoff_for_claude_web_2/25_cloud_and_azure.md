# 25 — Cloud, and the Azure trial

*New file, 2026-09-15. A workstream one day old. Everything here is exploratory except
the measurements, which are real.*

---

## 1. The ask

Mario, relayed by the user: he wants the code to run on **Azure**, so that
**"everyone in our group can run and test these codes"**. He asked us to register an
account and try it first.

Read the words carefully, because two different projects hide in them:

| reading | what it needs |
|---|---|
| **(a) everyone can EXECUTE the pricing** | a service they call — an HTTP endpoint |
| **(b) everyone can RUN AND TEST the code** | an environment they each get — a shell, a container, a dev box |

(b) is closer to the literal words and is what the trial pursued. (a) is what the
architecture was built for and is the natural second step — `endpoints/dependencies.py`
carries the docstring *"A cloud deployment that keeps its curves in object storage
replaces this file and nothing else,"* and the template's `endpoints/routes/` was
deferred explicitly "with the HTTP service".

**Account:** a free personal Azure subscription on the user's **Columbia email**
(`lc3904@columbia.edu`). ⚠️ That is a trial account, not a tenant Mario's group can be
added to. See §6.

---

## 2. ⭐ What the trial proved

Azure Cloud Shell, browser-based, free tier. Clone → venv → `pip install -r
requirements.txt` → `pytest`:

```
Linux x86_64 | Python 3.12.14
numpy 2.5.3 | pandas 3.0.5 | scipy 1.18.1
483 passed in 40.17s
```

Three things worth carrying into any plan:

1. **Everything passed on a materially newer scientific-Python stack** — pandas is a
   whole major version ahead of the development machine. Golden-master bootstrap,
   workbook loaders, the universe funnel's exact counts: all green. For a team about to
   take this to the cloud, that is a strong and cheaply-obtained fact.
2. **It is fast.** 40 s against ~50 s locally and ~230 s on `47`. The corporate book's
   driver ran in **7.9 s**.
3. ⭐ **Azure → GitHub has no GFW in the path.** The clone ran at 18 MB/s. The TLS
   resets and crawl-speed fetches documented for `47 → GitHub` simply do not occur,
   because neither end is behind it. That makes an Azure box a *better* GitHub client
   than the deployment host.

---

## 3. What runs without the client data — measured, three tiers

Built by copying the package and withholding parts of `data/`:

| tier | on the machine | result |
|---|---|---|
| ① code only, 1.5 MB | no data | 340 pass / 56 skip / **87 FAIL** — looks broken |
| ⭐ ② + market curves + our override tables, 14 MB | **no client portfolio, no proprietary workbooks** | **435 pass / 48 skip / 0 fail** |
| ③ + portfolio + workbooks, 35 MB | everything | 483 pass / 0 skip |

⭐ **`data/` is not one thing**, and knowing its composition is what made tier ② possible:

| | files | size |
|---|---:|---:|
| the client portfolio (URS holdings) | 1 | 3.4 MB |
| legacy pricing workbooks (Mario's proprietary VBA) | 2 | 11.1 MB |
| **market data: par-yield curve exports** | 26 | 14.2 MB |
| our own override tables | 6 | ~0 |

Tier ② has **zero failures** — the 48 skips are properly guarded. It prices a real bond
end to end. That is a complete, demonstrable deployment with no client holdings on it.

⚠️ **87 of the tier-① failures are data-dependent tests with NO skip guard** (41
endpoint, 19 wrapper, 9 fixture, 11 monthly-recon, 7 loader). A data-free deployment
therefore *looks* broken. Adding guards is an open follow-up; tier ② sidesteps it.

---

## 4. The client-data question, and how it was settled

It was raised before anything was uploaded: putting the URS pension portfolio on Azure
is a **new venue** for client data. The boss's 2026-07-08 approval covers a *private
GitHub repo*; the user's 2026-09-05 approval covers the *Drive delivery folder*, to
people who already hold the data. Neither obviously extends to a cloud tenant.

**Mario's answer, relayed 2026-09-15: the data is not sensitive.** That settles the
sensitivity question, and the repo was cloned whole (tier ③).

Two things remain true and are **not** sensitivity objections:

* the repo must still stay **private** on GitHub — unchanged, separate matter;
* ⚠️ the PAT used to clone is a credential. Scope it **read-only to one repo, short
  expiry**, paste it at git's password prompt (not on the command line, where it enters
  shell history), and revoke it after.

---

## 5. Cloud Shell mechanics — every trap hit, in order

Four separate obstacles, none of them about our code. Anyone repeating this will hit the
same four.

1. **`Microsoft.CloudShell` is not registered on a new subscription.** Azure resource
   providers are per-subscription opt-ins. Fix: `az provider register --namespace
   Microsoft.CloudShell`, then **restart** — the mount is established at session start,
   so registering inside a running session does nothing for that session.
2. ⭐ **Region mismatch — the actual cause of the failed mount.** Cloud Shell requires
   the storage account to be in the **same region as the container**:
   ```
   storage  Location     = eastus
   shell    ACC_LOCATION = EASTASIA   (cluster ae2prodhkcag-1)
   ```
   It places the container near the user (China → Hong Kong) while the storage account
   was created in the US on our advice — chosen for data residency, which is the wrong
   axis: the same-region requirement is a hard technical constraint and Mario has since
   said residency is not a concern. **Fix: reset Cloud Shell user settings, restart, and
   let Cloud Shell create the storage account itself** so it lands in the right region.
   Delete the orphan.
3. ⚠️ **Without a mount the session is EPHEMERAL and wipes on a ~20-minute idle
   timeout.** It wiped twice during the trial, losing the clone, the venv and the pip
   installs each time. Any back-and-forth with a human easily exceeds 20 minutes.
4. **The browser terminal mangles long multi-line pastes**, especially heredocs — a lost
   newline leaves the heredoc collecting input forever. ⇒ **put the work in a script in
   the repository** and paste one line. That is why `scripts/platform_parity.py` exists.

### Storage account settings that matter

Primary service **Azure Files** (Cloud Shell mounts a 5 GB SMB share at `~/clouddrive`),
performance **Standard**, redundancy **LRS** — the default GRS costs roughly double for
a home directory whose loss means re-cloning. ~$0.15–0.30/month.

⚠️ A storage account name becomes a **public DNS label**
(`<name>.blob.core.windows.net`), so it must carry no client identity. `fip…` is fine;
the client's name is not.

---

## 6. What "everyone in our group can run" actually needs

The trial answers *can it run*. It does not answer *can the group use it*.

| option | fits which reading | cost | notes |
|---|---|---|---|
| **Cloud Shell, per person** | (b) | free + ~$0.3/mo storage each | each person gets their own; needs the mount configured or it is ephemeral; needs a PAT to clone a private repo |
| **App Service / Container App** | (a) | F1 free tier: 1 GB RAM, **60 CPU-min/day** | gives a URL the Excel bridge could POST to instead of shelling out. numpy+pandas+scipy ≈ 250 MB installed — fits, tight. 60 min/day is a real cap for batch driver runs |
| **Azure Functions (consumption)** | (a) | 1M executions free | the closest fit to "one JSON in, one JSON out" |
| **A VM / Dev Box** | (b) | real money | shared state; simplest conceptually, least attractive |

⚠️ **A free Azure account is $200 of credit for 30 days**, after which only the
always-free services remain. Do not build something that silently starts charging.

⚠️ **A personal subscription on a university email is not where a group's shared
environment belongs.** That is not a data-sensitivity point — it is that Mario's stated
goal requires a tenant his group can be added to. **Which tenant is a question for
Mario**, and it is better asked with a working demo in hand than before one.

---

## 7. What the architecture already has for this

Nothing needs inventing for step (a):

* `endpoints/main.analyze_payload(payload) -> response` — one request in, one complete
  answer out, **failures are values rather than exceptions**;
* `endpoints/contracts.py` — the whole contract, standard library only;
* `endpoints/dependencies.py` — **the only environment-aware file**, and the one a cloud
  deployment replaces;
* `scripts/price_json.py` — file in, file out, exit 0/1/2;
* seven instrument types already supported by the contract.

The missing pieces are an HTTP wrapper, a container definition, and a decision about
where the curve files live (a mounted share, blob storage, or baked into the image).

---

## 8. Open

1. **Which tenant** — Mario's, so his group can be added. Ask after the demo.
2. **Which shape** — a shell each (b), or a called service (a). His words point at (b);
   his Excel proposal points at (a). Worth asking directly rather than guessing.
3. **The Cloud Shell mount** — reset and let Azure pick the region. Until then every
   session is ephemeral.
4. **`requirements.txt` has no upper version bounds** — see `24_determinism_and_cross_platform.md`.
5. **The 87 unguarded data-dependent tests** — a data-free deployment looks broken.
6. **The Azure parity result is UNRESOLVED** — the first run used a check that was itself
   broken (see `24`). Do not record a verdict until the fixed check has run there.
