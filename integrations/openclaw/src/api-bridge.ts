/**
 * Optional bridge to the Verdicto API for dashboard persistence.
 *
 * All operations are non-blocking and fail-safe. If the API is unreachable,
 * local proof generation continues unaffected.
 */

interface AgentPassResult {
  agent_pass: string;
  [key: string]: unknown;
}

interface VerifyResult {
  decision: string;
  verification_id: string;
  [key: string]: unknown;
}

export class APIBridge {
  private _baseUrl: string;
  private _apiKey: string;
  private _agentPassJwt: string | null = null;

  constructor(baseUrl: string, apiKey: string) {
    this._baseUrl = baseUrl.replace(/\/$/, "");
    this._apiKey = apiKey;
  }

  get enabled(): boolean {
    return Boolean(this._baseUrl && this._apiKey);
  }

  /** Issue an Agent Pass (cached after first call). */
  async ensureAgentPass(agentId: string): Promise<string | null> {
    if (this._agentPassJwt) return this._agentPassJwt;

    try {
      const res = await fetch(`${this._baseUrl}/v1/agent/pass/issue`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": this._apiKey,
        },
        body: JSON.stringify({
          sub: agentId,
          ttl_seconds: 900,
          scopes: ["openclaw.tool_call", "openclaw.web_browse"],
          currency_allowlist: ["USD"],
          merchant_allowlist: [agentId],
        }),
      });

      if (!res.ok) {
        console.warn(`[verdicto] Agent Pass issue failed: ${res.status}`);
        return null;
      }

      const data = (await res.json()) as AgentPassResult;
      this._agentPassJwt = data.agent_pass;
      return this._agentPassJwt;
    } catch (err) {
      console.warn(`[verdicto] Agent Pass issue error: ${err}`);
      return null;
    }
  }

  /** Send a verification request to the API (fire-and-forget). */
  async sendVerification(opts: {
    action: string;
    agentId: string;
    context?: Record<string, unknown>;
  }): Promise<void> {
    try {
      const agentPass = await this.ensureAgentPass(opts.agentId);

      const body: Record<string, unknown> = {
        requested_action: opts.action,
        subject_id: opts.agentId,
      };
      if (agentPass) body.agent_pass = agentPass;
      if (opts.context) body.context = opts.context;

      const res = await fetch(`${this._baseUrl}/v1/verify/agent`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": this._apiKey,
          "Idempotency-Key": crypto.randomUUID(),
        },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        const data = (await res.json()) as VerifyResult;
        console.log(
          `[verdicto] API verification: decision=${data.decision} id=${data.verification_id}`
        );
      }
    } catch (err) {
      console.warn(`[verdicto] API verification failed (non-fatal): ${err}`);
    }
  }
}
