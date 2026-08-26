# Putting Chaos Draft on the internet

**Why bother:** a laptop hotspot caps at 8 devices and a phone at about 10, against
roughly 30 participants. Any answer that puts everyone on one local network is
dead on that number alone. Hosting it publicly means each person reaches it on
their own mobile data, so no shared network is needed and it does not matter
whether the venue's wifi works.

The server reads its own address from the incoming request, so the join QR is
correct wherever it ends up. There is nothing to configure after deploying.

---

## Render (first choice)

Free, no card, supports WebSockets, and deploys straight from this repo.

1. [render.com](https://render.com) &rarr; **Get Started** &rarr; sign in with GitHub
2. **New** &rarr; **Blueprint**
3. Pick `accelerate-muj/git-started`
4. Apply. It reads `render.yaml` at the repo root.

About three minutes. You get `https://chaos-draft-XXXX.onrender.com`.

**Free instances sleep after ~15 minutes of no traffic** and take about a minute
to wake. Chaos Draft runs in the first fifteen minutes of the session, so open the
URL yourself while people are settling in. It will be warm by the time the QR is
on the projector.

### If GitHub sign-in will not work

Almost always the browser, not Render or GitHub. In rough order:

1. **Try a different browser.** Privacy-focused browsers (Comet, Brave, Arc with
   shields up) block third-party cookies and popups, and OAuth needs both. Chrome
   or Edge usually just works.
2. **Allow popups** for `render.com`, then retry.
3. **Turn off ad blockers and privacy extensions** for `render.com`, then retry.
4. **Sign up with email instead.** Render supports email and password. Create the
   account that way, then connect GitHub afterwards from
   **Account Settings &rarr; Connected Accounts**, which is a different flow and
   often succeeds when the login popup does not.
5. **Check the org is not restricting OAuth apps.** For `accelerate-muj` it is
   not, so this is unlikely to be it, but for another org:
   **Settings &rarr; Third-party Access**.

If none of that works, use Hugging Face below. It takes an email address and never
needs GitHub.

---

## Hugging Face Spaces (fallback, no GitHub needed)

Free, no card, no GitHub OAuth, and it does not sleep as aggressively as Render.

1. Create an account at [huggingface.co](https://huggingface.co) with an email
   address.
2. **New** &rarr; **Space**. Name it, pick **Docker** as the SDK, set it public.
3. Clone the empty Space and copy this folder into it:

```bash
git clone https://huggingface.co/spaces/YOUR-NAME/chaos-draft hf-space
```

```bash
cp -r chaos-draft/* hf-space/
```

4. Spaces need a `README.md` at the root with this frontmatter, so replace the one
   you just copied in:

```
---
title: Chaos Draft
emoji: 🖊️
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

Collaborative writing warm-up for Accelerate's git workshop.
```

5. Push:

```bash
cd hf-space && git add . && git commit -m "Chaos Draft" && git push
```

The `Dockerfile` in this folder already listens on `$PORT`, which Spaces sets to
7860. You get `https://YOUR-NAME-chaos-draft.hf.space`.

---

## Anything else that runs a container

The `Dockerfile` is plain and has no host-specific anything in it. Koyeb, Fly and
Railway all work, though the last two want a card on file.

Two requirements wherever it goes:

- **WebSockets must be supported.** The shared document is built on a persistent
  connection. This rules out Vercel and Netlify functions, which are serverless
  and do not hold connections open. You would need a separate realtime service
  bolted on, which is more moving parts than picking a host that does it natively.
- **`uvicorn[standard]`, not plain `uvicorn`.** Already pinned in
  `requirements.txt`. Plain uvicorn ships no WebSocket library, so the app builds
  cleanly, starts cleanly, and then refuses every connection. Verified in a clean
  virtualenv: with plain uvicorn both `websockets` and `wsproto` are absent.

---

## Running it locally instead

Still fine for a small group, or for testing:

```bash
cd chaos-draft && python server.py
```

It prints a QR and a LAN address. Everyone on the same wifi or hotspot can join,
up to whatever your hotspot allows. See the [README](README.md) for the firewall
rule and the client-isolation problem.
