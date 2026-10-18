# Graph Hacks: verified requirements

Rechecked October 18, 2026 against organizer sources. Deadline: **October 18, 2026, 11:59 PM IST**. Event began October 15, 12:01 AM IST. Recheck announcements before submitting.

## Track 1

**Agents That Act on Connected Data**: build an agent that uses the graph to decide and act. Published focus areas:

1. Multi-hop reasoning.
2. Graph queries and algorithms as agent tools.
3. Tool selection through MCP.
4. Actions based on what the graph shows.
5. Explainable results.

These are track focus areas; the published rules do not specify a numerical judging rubric, minimum dataset size, required LLM provider, or mandatory algorithm count. Treat MCP as a feature we intend to demonstrate, not an excuse to substitute a chat client for a working product.

## Binding rules and project evidence

| Rule | Evidence we will supply |
| --- | --- |
| FalkorDB is the primary graph database and central to the product | Real graph tools; database outage fails the investigation; edge changes alter decisions |
| A visualization on ordinary storage is insufficient | Traversals return evidence consumed by policy and action tools |
| Public, synthetic or own permitted data only; restricted/private data is disallowed | Deterministic synthetic fixtures, provenance document, no real identity or payment data |
| Main coding/design and main FalkorDB work are new work during the event | Repository history, original domain model, verification records |
| Solo or maximum four members; one team per participant | Confirm registration and actual registered members |
| AI assistants are allowed with disclosure | README assistance disclosure and participant architecture walkthrough |
| Participant understands code and decisions | Explain each edge, query, tool, policy and failure mode |
| Entry must identify its track | Track 01 in README and submission form |

Any language/framework/platform is allowed. Docker, self-hosting and FalkorDB Cloud are accepted. Live deployment is preferred; complete local instructions plus a working demo video are an accepted alternative.

## Submission checklist

- [ ] Register participant/team through WeMakeDevs; confirm in signed-in portal.
- [x] Public source repository, accessible without login.
- [x] README with complete setup instructions.
- [x] Graph data model in README (or clearly linked from it).
- [x] Actual Cypher queries/graph algorithms the product depends on.
- [x] Demo video showing working end-to-end behavior.
- [x] Live deployment, or complete reproducible local setup.
- [ ] Track 01 explicitly selected in submission.
- [x] AI assistance disclosed.
- [x] No secrets, private data, broken links or unlicensed assets.
- [ ] Submission saved and checked before October 18, 11:59 PM IST.

The public pages do not establish video duration, form-specific fields, weighted judging criteria, or final upload constraints. Check the authenticated submission portal rather than inventing requirements. The participant is signed in separately in Chrome. Registration/team state and the final saved submission have not been verified from this chat. The public repository, demo film, local setup, graph model, executed Cypher, disclosures, and submission copy are prepared; see [submission.md](submission.md).

The main page and rules permit multiple tracks. The organizer tutorial contains narrower wording about entering one; for this project there is no practical conflict because our chosen entry is Track 01 only.

## Sources

- [Brief, tracks and FAQ](https://www.wemakedevs.org/hackathons/falkordb)
- [Rules](https://www.wemakedevs.org/hackathons/falkordb/rules)
- [Schedule](https://www.wemakedevs.org/hackathons/falkordb/schedule)
- [Resources](https://www.wemakedevs.org/hackathons/falkordb/resources)
- [Organizer implementation guide](https://www.wemakedevs.org/blogs/how-to-build-an-agent-that-reasons-over-a-graph)
