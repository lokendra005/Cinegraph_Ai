import { useCallback, useEffect, useState } from "react";

const SAMPLE_STORIES = [
  {
    label: "Best Demo",
    title: "The Last Transmission",
    input: `A retired astronaut, Arjun Sen, receives nightly radio bursts in his dead co-pilot Mira's voice. The first message is fragmented, but it repeats a private code phrase only they knew. Arjun reopens his abandoned observatory and maps the transmissions against old mission logs. As the messages become clearer, they reveal guilt buried from a failed rescue maneuver Arjun never confessed. In parallel, Arjun's daughter confronts him about his obsession and emotional absence. During a storm blackout, the final signal arrives with coordinates and one sentence: "You were never alone in that decision." Arjun drives to a decommissioned tracking station at dawn, records a final reply, and chooses reconciliation over self-punishment.`,
  },
  {
    label: "Emotional",
    title: "The Last Signal",
    input: `A retired astronaut receives radio messages from his dead co-pilot. At first he thinks it's a malfunction. As messages continue, he realizes the transmission is real. He spirals into obsession, spending nights in his observatory trying to decode the messages.`,
  },
  {
    label: "Action",
    title: "Skyward Heist",
    input: `A hacker infiltrates a floating cyberpunk city. She needs to steal a biometric encryption key from the central tower. With her team monitoring from outside, she uses parkour and hacking tools to navigate through security systems and guards. She escapes with the key before the tower explodes.`,
  },
  {
    label: "Ambiguous",
    title: "The Letter",
    input: `A woman opens a letter. Her hands tremble. She reads silently, tears streaming down her face. The camera pans to show an empty living room. A wedding photo on the shelf is turned face-down. She sits alone at a table, the letter crumpled in her hand. Outside, rain falls.`,
  },
];

type StoryResp = {
  id: string;
  title: string;
  status: string;
  seed: number;
  error_message: string | null;
  parsed: Record<string, unknown> | null;
};

type JobResp = {
  id: string;
  story_id: string;
  status: string;
  attempts: number;
  max_attempts: number;
  last_error: string | null;
  use_llm: boolean;
};

type StoryboardFrame = {
  url: string;
  frame_index: number;
  prompt_meta?: {
    positive_prompt?: string;
    negative_prompt?: string;
    style_reference?: string;
    aspect_ratio?: string;
    seed?: number;
    frame_beat?: string;
  };
};

type StoryboardScene = {
  scene_id: string;
  scene_number: number;
  title: string;
  frames: StoryboardFrame[];
};

type StoryboardPayload = {
  scenes: StoryboardScene[];
};

export function App() {
  const [title, setTitle] = useState(SAMPLE_STORIES[0].title);
  const [input, setInput] = useState(SAMPLE_STORIES[0].input);
  const [seed, setSeed] = useState(42);
  const [useLlm, setUseLlm] = useState(true);
  const [busy, setBusy] = useState(false);
  const [storyId, setStoryId] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<JobResp | null>(null);
  const [jobHistory, setJobHistory] = useState<JobResp[]>([]);
  const [story, setStory] = useState<StoryResp | null>(null);
  const [scenes, setScenes] = useState<unknown[]>([]);
  const [storyboard, setStoryboard] = useState<unknown | null>(null);
  const [trace, setTrace] = useState<unknown | null>(null);
  const [evaluation, setEvaluation] = useState<unknown | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [videoBusy, setVideoBusy] = useState(false);
  const [autoVideo, setAutoVideo] = useState(true);
  const [videoRequestStoryId, setVideoRequestStoryId] = useState<string | null>(null);
  const [sceneClipUrls, setSceneClipUrls] = useState<Record<string, string>>({});
  const [sceneClipBusy, setSceneClipBusy] = useState<Record<string, boolean>>({});
  const [selectedFrame, setSelectedFrame] = useState<{
    scene: StoryboardScene;
    frame: StoryboardFrame;
  } | null>(null);

  const poll = useCallback(async (id: string, jId?: string | null) => {
    const requests = [
      fetch(`/api/v1/stories/${id}`).then((r) => r.json()),
      fetch(`/api/v1/stories/${id}/scenes`).then((r) => r.json()),
      fetch(`/api/v1/stories/${id}/storyboard`).then((r) => r.json()),
      fetch(`/api/v1/stories/${id}/trace`).then((r) => r.json()),
      fetch(`/api/v1/stories/${id}/evaluation`).then((r) => r.json()),
      fetch(`/api/v1/stories/${id}/jobs`).then((r) => r.json()),
    ] as const;
    const all = jId
      ? [...requests, fetch(`/api/v1/jobs/${jId}`).then((r) => r.json())]
      : requests;
    const [s, sc, sb, tr, ev, jobs, j] = (await Promise.all(all)) as [
      StoryResp,
      unknown,
      unknown,
      unknown,
      unknown,
      unknown,
      JobResp | undefined
    ];
    setStory(s);
    setScenes(Array.isArray(sc) ? sc : []);
    setStoryboard(sb);
    setTrace(tr);
    setEvaluation(ev);
    setJobHistory(Array.isArray(jobs) ? (jobs as JobResp[]) : []);
    if (j) setJob(j);
    try {
      const vr = (await fetch(`/api/v1/stories/${id}/video`).then((r) => r.json())) as {
        ready?: boolean;
        video_url?: string | null;
        scene_clips?: Array<{ scene_id: string; video_url: string }>;
      };
      setVideoUrl(vr?.ready ? vr.video_url ?? null : null);
      if (Array.isArray(vr?.scene_clips)) {
        setSceneClipUrls((prev) => {
          const next = { ...prev };
          for (const c of vr.scene_clips ?? []) {
            if (c.scene_id && c.video_url) next[c.scene_id] = c.video_url;
          }
          return next;
        });
      }
    } catch {
      setVideoUrl(null);
    }
    return s as StoryResp;
  }, []);

  useEffect(() => {
    if (!storyId) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const s = await poll(storyId, jobId);
        if (cancelled) return;
        if (s.status === "completed" || s.status === "failed") {
          return true;
        }
      } catch {
        if (!cancelled) setErr("Poll failed");
      }
      return false;
    };
    let interval: ReturnType<typeof setInterval> | undefined;
    tick().then((done) => {
      if (done) return;
      interval = setInterval(async () => {
        const d = await tick();
        if (d && interval) clearInterval(interval);
      }, 1500);
    });
    return () => {
      cancelled = true;
      if (interval) clearInterval(interval);
    };
  }, [storyId, jobId, poll]);

  async function submit() {
    setErr(null);
    setBusy(true);
    try {
      const res = await fetch("/api/v1/stories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          input,
          input_type: "text",
          seed,
          use_llm: useLlm,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setStoryId(data.story_id);
      setJobId(data.job_id);
      setVideoUrl(null);
      setVideoRequestStoryId(null);
      setSceneClipUrls({});
      setSceneClipBusy({});
      await poll(data.story_id, data.job_id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function regenerate() {
    if (!storyId) return;
    setErr(null);
    setBusy(true);
    try {
      const res = await fetch(`/api/v1/stories/${storyId}/regenerate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ seed, use_llm: useLlm }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setJobId(data.job_id);
      setVideoUrl(null);
      setVideoRequestStoryId(null);
      setSceneClipUrls({});
      setSceneClipBusy({});
      await poll(storyId, data.job_id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  async function cancelJob() {
    if (!jobId) return;
    setErr(null);
    try {
      const res = await fetch(`/api/v1/jobs/${jobId}/cancel`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      if (storyId) await poll(storyId, jobId);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Cancel failed");
    }
  }

  const metrics =
    evaluation &&
    typeof evaluation === "object" &&
    "metrics" in evaluation &&
    (evaluation as { metrics: Record<string, number> }).metrics;
  const storyboardScenes =
    storyboard && typeof storyboard === "object" && "scenes" in storyboard
      ? ((storyboard as StoryboardPayload).scenes ?? [])
      : [];

  const sceneMetaByNumber = new Map<
    number,
    { planner?: Record<string, unknown>; director?: Record<string, unknown>; script?: Record<string, unknown> }
  >();
  for (const sc of scenes as Array<{
    scene_number: number;
    metadata?: { planner?: Record<string, unknown>; director?: Record<string, unknown>; script?: Record<string, unknown> };
  }>) {
    sceneMetaByNumber.set(sc.scene_number, {
      planner: sc.metadata?.planner,
      director: sc.metadata?.director,
      script: sc.metadata?.script,
    });
  }

  function copyPrompt(text: string) {
    navigator.clipboard.writeText(text).catch(() => {});
  }

  async function generateVideo() {
    if (!storyId) return;
    setVideoBusy(true);
    setErr(null);
    try {
      const res = await fetch(`/api/v1/stories/${storyId}/video`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      const data = (await res.json()) as { video_url?: string };
      setVideoUrl(data.video_url || null);
      if (storyId) setVideoRequestStoryId(storyId);
      const vr = (await fetch(`/api/v1/stories/${storyId}/video`).then((r) => r.json())) as {
        scene_clips?: Array<{ scene_id: string; video_url: string }>;
      };
      if (Array.isArray(vr.scene_clips)) {
        setSceneClipUrls((prev) => {
          const next = { ...prev };
          for (const c of vr.scene_clips ?? []) {
            if (c.scene_id && c.video_url) next[c.scene_id] = c.video_url;
          }
          return next;
        });
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Video generation failed");
    } finally {
      setVideoBusy(false);
    }
  }

  async function generateSceneClip(sceneId: string) {
    if (!storyId) return;
    setSceneClipBusy((b) => ({ ...b, [sceneId]: true }));
    setErr(null);
    try {
      const res = await fetch(`/api/v1/stories/${storyId}/scenes/${sceneId}/video`, { method: "POST" });
      if (!res.ok) throw new Error(await res.text());
      const data = (await res.json()) as { video_url?: string };
      if (data.video_url) setSceneClipUrls((u) => ({ ...u, [sceneId]: data.video_url! }));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Scene clip failed");
    } finally {
      setSceneClipBusy((b) => ({ ...b, [sceneId]: false }));
    }
  }

  useEffect(() => {
    if (!autoVideo || !storyId || !story || videoBusy) return;
    if (story.status !== "completed") return;
    if (videoUrl) return;
    if (videoRequestStoryId === storyId) return;
    void generateVideo();
  }, [autoVideo, storyId, story, videoBusy, videoUrl, videoRequestStoryId]);

  return (
    <>
      <h1>CineGraph AI</h1>
      <p className="subtitle">
        Deterministic multi-agent narrative → screenplay → cinematic plan → storyboard frames. Scene films add motion,
        dissolves between shots, and on-screen dialogue (not raw text-to-video, but a structured clip per scene).
      </p>

      <div className="panel">
        <h2>Story input</h2>
        <div className="row" style={{ marginBottom: "0.75rem" }}>
          {SAMPLE_STORIES.map((s) => (
            <button
              key={s.label}
              type="button"
              className="secondary"
              style={{ flex: "0 auto", fontSize: "0.8rem", padding: "0.4rem 0.75rem" }}
              onClick={() => {
                setTitle(s.title);
                setInput(s.input);
              }}
            >
              {s.label}
            </button>
          ))}
        </div>
        <div className="row">
          <div>
            <label htmlFor="title">Title</label>
            <input id="title" type="text" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <div>
            <label htmlFor="seed">Seed</label>
            <input
              id="seed"
              type="text"
              inputMode="numeric"
              value={seed}
              onChange={(e) => setSeed(parseInt(e.target.value || "0", 10) || 0)}
            />
          </div>
        </div>
        <label htmlFor="input">Narrative</label>
        <textarea id="input" value={input} onChange={(e) => setInput(e.target.value)} />
        <div className="row" style={{ marginTop: "1rem", alignItems: "center" }}>
          <label className="checkbox">
            <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} />
            Use LLM when API key configured (falls back offline)
          </label>
          <label className="checkbox">
            <input type="checkbox" checked={autoVideo} onChange={(e) => setAutoVideo(e.target.checked)} />
            Auto-generate MP4 after compile
          </label>
          <button type="button" disabled={busy} onClick={() => void submit()}>
            Compile story {autoVideo ? "+ video" : ""}
          </button>
          {storyId && (
            <button type="button" className="secondary" disabled={busy} onClick={() => void regenerate()}>
              Regenerate
            </button>
          )}
        </div>
        {err && <div className="status failed">{err}</div>}
        {story && (
          <div className={`status ${story.status === "completed" ? "completed" : ""} ${story.status === "failed" ? "failed" : ""}`}>
            Story: {story.id.slice(0, 8)}… · status: {story.status}
            {story.error_message ? ` · ${story.error_message}` : ""}
          </div>
        )}
        {job && (
          <div className={`status ${job.status === "completed" ? "completed" : ""} ${job.status === "failed" || job.status === "cancelled" ? "failed" : ""}`}>
            Job: {job.id.slice(0, 8)}… · status: {job.status} · attempts: {job.attempts}/{job.max_attempts}
            {job.last_error ? ` · ${job.last_error}` : ""}
          </div>
        )}
        {jobId && job && job.status === "queued" && (
          <div style={{ marginTop: "0.75rem" }}>
            <button type="button" className="secondary" onClick={() => void cancelJob()}>
              Cancel queued job
            </button>
          </div>
        )}
        {jobHistory.length > 0 && (
          <div style={{ marginTop: "0.75rem" }}>
            <label style={{ marginBottom: "0.5rem" }}>Job history</label>
            <div className="trace" style={{ maxHeight: "180px" }}>
              {jobHistory.map((j) => (
                <div key={j.id} style={{ marginBottom: "0.35rem" }}>
                  {j.id.slice(0, 8)}… · {j.status} · attempts {j.attempts}/{j.max_attempts}
                  {j.last_error ? ` · ${j.last_error}` : ""}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {metrics && (
        <div className="panel">
          <h2>Evaluation</h2>
          <div className="metrics">
            {Object.entries(metrics).map(([k, v]) =>
              typeof v === "number" ? (
                <div key={k} className="metric">
                  <div className="val">{v}</div>
                  <div className="lbl">{k.replace(/_/g, " ")}</div>
                </div>
              ) : null
            )}
          </div>
          {evaluation &&
            typeof evaluation === "object" &&
            "overall_score" in evaluation && (
            <p style={{ marginTop: "1rem", color: "var(--muted)", fontSize: "0.9rem" }}>
              Overall:{" "}
              <strong style={{ color: "var(--accent)" }}>
                {String((evaluation as { overall_score: number }).overall_score)}
              </strong>
            </p>
          )}
        </div>
      )}

      {scenes.length > 0 && (
        <div className="panel">
          <h2>Scene timeline</h2>
          <div className="timeline">
            {scenes.map((sc: unknown) => {
              const s = sc as {
                scene_number: number;
                title: string;
                location: string | null;
                metadata: { planner?: { emotional_tone?: string; transition_type?: string } };
              };
              return (
                <div key={s.scene_number} className="scene-card">
                  <strong>
                    {s.scene_number}. {s.title}
                  </strong>
                  <div className="meta">{s.location || "—"}</div>
                  <div className="meta">
                    {s.metadata?.planner?.emotional_tone} · {s.metadata?.planner?.transition_type}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {storyboardScenes.length > 0 && (
          <div className="panel">
            <h2>Storyboard</h2>
            <div className="row" style={{ marginBottom: "0.6rem", alignItems: "center", flexWrap: "wrap", gap: "0.5rem" }}>
              <button type="button" className="secondary" disabled={videoBusy} onClick={() => void generateVideo()}>
                {videoBusy ? "Generating full film..." : "Generate full film (all scenes)"}
              </button>
              {videoUrl && (
                <a href={videoUrl} download className="secondary" style={{ textDecoration: "none", padding: "0.6rem 1rem" }}>
                  Download full film
                </a>
              )}
            </div>
            <p style={{ fontSize: "0.85rem", color: "var(--muted)", marginBottom: "0.75rem" }}>
              Full film chains scene clips (title slate, camera motion, crossfades, subtitles). Use each scene&apos;s button
              for a standalone MP4 of that scene only.
            </p>
            {videoUrl && (
              <div style={{ marginBottom: "0.8rem" }}>
                <video controls style={{ width: "100%", borderRadius: "10px", border: "1px solid var(--border)" }} src={videoUrl} />
              </div>
            )}
            <div className="storyboard-scenes">
              {storyboardScenes.map((scene) => {
                const m = sceneMetaByNumber.get(scene.scene_number);
                const planner = m?.planner ?? {};
                const director = m?.director ?? {};
                const script = m?.script ?? {};
                const beats = Array.isArray(script.beats) ? (script.beats as string[]) : [];
                const dialogues = Array.isArray(script.dialogues)
                  ? (script.dialogues as Array<{ speaker?: string; line?: string }>)
                  : [];
                return (
                  <div key={`scene-${scene.scene_number}`} className="scene-section">
                    <div className="scene-head">
                      <div>
                        <strong>
                          Scene {scene.scene_number}: {scene.title}
                        </strong>
                        <div className="scene-sub">
                          {String(planner.location ?? "Unknown location")} · {String(planner.time_of_day ?? "")}
                        </div>
                        <div className="row" style={{ marginTop: "0.5rem", gap: "0.5rem", flexWrap: "wrap" }}>
                          <button
                            type="button"
                            className="secondary"
                            style={{ fontSize: "0.8rem", padding: "0.35rem 0.65rem" }}
                            disabled={!!sceneClipBusy[scene.scene_id]}
                            onClick={() => void generateSceneClip(scene.scene_id)}
                          >
                            {sceneClipBusy[scene.scene_id] ? "Scene MP4…" : "Scene MP4 only"}
                          </button>
                          {sceneClipUrls[scene.scene_id] && (
                            <a
                              href={sceneClipUrls[scene.scene_id]}
                              download
                              className="secondary"
                              style={{ textDecoration: "none", fontSize: "0.8rem", padding: "0.35rem 0.65rem" }}
                            >
                              Download scene clip
                            </a>
                          )}
                        </div>
                        {sceneClipUrls[scene.scene_id] && (
                          <video
                            controls
                            style={{
                              width: "100%",
                              maxWidth: "520px",
                              marginTop: "0.5rem",
                              borderRadius: "8px",
                              border: "1px solid var(--border)",
                            }}
                            src={sceneClipUrls[scene.scene_id]}
                          />
                        )}
                      </div>
                      <div className="scene-tags" title="Cinematic tags from planner + director agents (pacing = suggested edit rhythm, not video playback speed)">
                        <span>{String(planner.emotional_tone ?? "tone")}</span>
                        <span>{String(director.shot_type ?? "shot")}</span>
                        <span>{String(planner.transition_type ?? "cut")}</span>
                        {director.pacing != null && director.pacing !== "" && (
                          <span>Pacing: {String(director.pacing)}</span>
                        )}
                      </div>
                    </div>

                    {Boolean(script.synopsis) && <p className="scene-synopsis">{String(script.synopsis)}</p>}

                    {(beats.length > 0 || dialogues.length > 0) && (
                      <div className="scene-script-grid">
                        {beats.length > 0 && (
                          <div>
                            <div className="scene-kicker">Beats</div>
                            <ul className="scene-list">
                              {beats.slice(0, 3).map((b, i) => (
                                <li key={`${scene.scene_number}-beat-${i}`}>{String(b)}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                        {dialogues.length > 0 && (
                          <div>
                            <div className="scene-kicker">Dialogue</div>
                            <ul className="scene-list">
                              {dialogues.slice(0, 2).map((d, i) => (
                                <li key={`${scene.scene_number}-dlg-${i}`}>
                                  <strong>{d.speaker || "Voice"}:</strong> {d.line || ""}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}

                    <div className="storyboard-grid">
                      {scene.frames.map((f) => (
                        <button
                          key={`${scene.scene_number}-${f.frame_index}`}
                          type="button"
                          className="frame-card frame-button"
                          onClick={() => setSelectedFrame({ scene, frame: f })}
                          title="Open frame details"
                        >
                          <img src={f.url} alt={`${scene.title} frame ${f.frame_index + 1}`} />
                          <div className="cap">
                            Frame {f.frame_index + 1}
                            {f.prompt_meta?.frame_beat ? ` · ${f.prompt_meta.frame_beat}` : ""}
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

      {trace && (
        <div className="panel">
          <h2>Agent trace</h2>
          <pre className="trace">{JSON.stringify(trace, null, 2)}</pre>
        </div>
      )}

      {selectedFrame && (
        <div className="modal-backdrop" onClick={() => setSelectedFrame(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <h3>
                Scene {selectedFrame.scene.scene_number} · {selectedFrame.scene.title} · frame{" "}
                {selectedFrame.frame.frame_index + 1}
              </h3>
              <button type="button" className="secondary" onClick={() => setSelectedFrame(null)}>
                Close
              </button>
            </div>
            <img className="modal-image" src={selectedFrame.frame.url} alt="" />
            <div className="modal-grid">
              <div>
                <h4>Prompt metadata</h4>
                <pre className="trace">
{JSON.stringify(selectedFrame.frame.prompt_meta ?? {}, null, 2)}
                </pre>
              </div>
              <div>
                <h4>Scene metadata</h4>
                <pre className="trace">
{JSON.stringify(sceneMetaByNumber.get(selectedFrame.scene.scene_number) ?? {}, null, 2)}
                </pre>
              </div>
            </div>
            {sceneMetaByNumber.get(selectedFrame.scene.scene_number)?.script && (
              <div style={{ marginTop: "0.75rem" }}>
                <h4 style={{ margin: "0 0 0.35rem", color: "var(--muted)", fontSize: "0.8rem" }}>Script preview</h4>
                <pre className="trace">
{JSON.stringify(sceneMetaByNumber.get(selectedFrame.scene.scene_number)?.script ?? {}, null, 2)}
                </pre>
              </div>
            )}
            {selectedFrame.frame.prompt_meta?.positive_prompt && (
              <div style={{ marginTop: "0.6rem", display: "flex", gap: "0.6rem" }}>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => copyPrompt(selectedFrame.frame.prompt_meta?.positive_prompt || "")}
                >
                  Copy positive prompt
                </button>
                <a href={selectedFrame.frame.url} download className="secondary" style={{ textDecoration: "none", padding: "0.65rem 1rem" }}>
                  Download frame
                </a>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
