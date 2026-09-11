---
name: facebook-excavator-lead
description: "Find and export one verified Facebook excavator purchase or fleet-growth lead from a user-authorized browser session. Use for focused equipment lead research, not broad scraping or outreach."
---

# Facebook Excavator Lead

Find exactly one credible excavator lead and export it as a CSV record. Favor a direct purchase request; a verified project or fleet-expansion signal may qualify as a clearly labeled medium-intent lead.

## Scope and authorization

- Work only in a browser session the user has authorized, such as a supplied CDP endpoint, and only with content the signed-in user can normally view.
- Never bypass a login wall, CAPTCHA, group-access rule, or other platform restriction. Stop and ask the user to handle any such step.
- Do not join groups, react, comment, send messages, open external contact links, or otherwise contact a prospect unless the user separately asks for that action.
- Collect only business-relevant information shown in the post. Do not collect private contact details, account notifications, friend suggestions, or unrelated page content.
- When using a supplied CDP browser with `agent-browser`, use a named session and pin its tab so concurrent agents do not navigate the same tab accidentally.

## Define the search scope

- Use the user-supplied market, language, equipment type, purchase mode, and whether medium-intent project leads are allowed. If any choice would materially change the result, ask before searching. A general trial is allowed only when the user explicitly authorizes it.
- Work in one country, state/province, or metropolitan area per run whenever possible. State the assumed scope in the result.
- Prefer posts from the last 30 days. Older posts may be used only when their recency remains meaningful and is stated in the CSV.
- Search public posts first and then relevant groups already visible to the user. Build a small reusable candidate list of local construction, dirt-work, demolition, land-clearing, civil-work, and heavy-equipment groups; do not join groups to expand access.

## Search in two lanes

Use both applicable lanes before reporting that no lead was found. Adapt wording, brands, tonnage, and language to the scope.

### 1. Direct procurement — high intent

Search for explicit requests such as "looking for excavator", "excavator wanted", "WTB excavator", "need [model] excavator", "buy used excavator", "new excavator quote", or "request a quote", paired with the target location or job type.

Accept only a current, original post that expresses an intent to buy, obtain a quote, or source an excavator. Prefer a stated brand/model, size, condition, quantity, use case, delivery location, budget, or deadline.

### 2. Project or fleet expansion — medium intent

Use project terms such as land clearing, site work, grading, demolition, utility trenching, subdivision, or civil construction, paired with the target location. Use expansion terms such as "adding to our team", "hiring heavy equipment operator", or "new project" only when they identify an operating contractor.

Accept a medium-intent lead only when a named contractor has a recent, concrete expansion signal: for example, a new project, an additional crew, or hiring for excavator-capable heavy-equipment operators. Record it as a project/fleet-growth lead, never as an explicit purchase request.

Reject staffing agencies, generic service advertisements, a single vague job opening, job seekers, suppliers, dealers, resale posts, equipment advertisements, industry commentary, reposts without the original signal, and any result without a verifiable source link or time.

## Verify before export

Verify these in the rendered page before exporting:

- company or author;
- location or an explicit `未公开` value;
- publication time;
- the direct purchase statement or concrete expansion evidence;
- direct post URL.

Do not infer a budget, fleet size, machine specification, or intent not expressed in the post.

## Single-result output rule

- Return at most one lead per invocation. Continue searching until one meets the qualification rule, or report that no credible lead was found in the agreed search scope.
- Assign `高` only to a direct and current purchase/quote request. Assign `中` only to a verified project or fleet-expansion signal when the user permits medium-intent leads. Do not export `低`-intent leads.
- Export one CSV row using GBK (code page 936) unless the user specifies another encoding. Use a date-stamped filename such as `facebook_excavator_lead_YYYY-MM-DD.csv`.
- Include these fields: `客户名称`, `客户类型`, `地区`, `意向等级`, `需求类型`, `需求摘要`, `发布时间`, `来源小组或页面`, `原帖链接`, `公开联系方式`, `发现日期`, `备注`.
- Leave unknown values as `未公开`; use `Facebook 私信` only when the post explicitly invites a message. Never add scraped phone numbers or personal email addresses by default.

## Human-in-the-loop (HITL)

Pause and ask the user to act in these cases:

- Facebook requires a password, two-factor code, suspicious-login verification, CAPTCHA, or any other account-security check.
- Chrome asks to allow remote debugging, or the supplied CDP endpoint is unavailable.
- A target group is private, asks membership questions, requires admin approval, or otherwise restricts access.
- The search scope is materially incomplete and the user has not authorized a trial scope.
- The user asks to join a group, follow a profile, react, comment, message a prospect, click an external WhatsApp/email/phone link, or submit a contact form. Obtain explicit confirmation immediately before the action.

Do not treat an inaccessible post, ambiguous location, or missing contact method as a reason to bypass a restriction. Skip it or record `未公开` where the qualification criteria still hold.

## Delivery

State the lead's qualification basis and intent level in one concise sentence, link the CSV, and mention material limits such as inaccessible groups, missing geography, or exclusion of direct purchase leads. Do not expose unrelated browser content in the response.
