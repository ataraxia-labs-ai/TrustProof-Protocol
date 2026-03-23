# Demo Session

A typical OpenClaw session with TrustProof generation:

## Agent Session

```
User: Find the best noise-canceling headphones under $300 and compare them.

[verdicto] TrustProof generated: openclaw.tool_call.web_search (chain: 1 proofs)
Agent: Searching for noise-canceling headphones...

[verdicto] TrustProof generated: openclaw.web_browse.navigate (chain: 2 proofs)
Agent: Browsing rtings.com for detailed reviews...

[verdicto] TrustProof generated: openclaw.tool_call.web_search (chain: 3 proofs)
Agent: Checking current prices across retailers...

[verdicto] TrustProof generated: openclaw.tool_call.code_execute (chain: 4 proofs)
Agent: Creating comparison table...

Agent: Here are the top 3 options:
| Model | Price | Rating | Noise Canceling |
|-------|-------|--------|-----------------|
| Sony WH-1000XM5 | $278 | 9.2/10 | Excellent |
| Bose QC Ultra | $299 | 8.9/10 | Excellent |
| Apple AirPods Max | $449 | 8.7/10 | Very Good |

[verdicto] Session ended: 4 proofs, chain integrity: VALID
```

## Trust Verification

The agent can verify its own chain:

```
User: Verify your trust chain before I proceed with a purchase.

Agent: Let me check my trust chain integrity.
→ trustproof_verify_chain: { valid: true, proof_count: 4, errors: [] }

Agent: My trust chain is intact. All 4 actions have been cryptographically
signed and chain-linked. You can export this audit trail for records.
```

## Export

```
User: Export the proof chain.

→ trustproof_export: [
    "eyJhbGciOiJFZERTQSIs...",  // web_search
    "eyJhbGciOiJFZERTQSIs...",  // web_browse.navigate
    "eyJhbGciOiJFZERTQSIs...",  // web_search
    "eyJhbGciOiJFZERTQSIs..."   // code_execute
  ]
```

Each JWT is independently verifiable with the agent's public key.
