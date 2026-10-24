from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# First course rebuilt from the closed Xpress Digital store: "The Xpress
# Selling System" ebook (5-phase email automation playbook) merged with
# "The Complete Guide to Email List Marketing". Rewritten in Academy
# style — invented statistics and unverifiable "success story" claims
# from the ebooks were dropped; tool/platform details are phrased so
# they don't go stale (free-plan limits change, so learners are told to
# check). Several lessons per module plus a module quiz, unlike the
# older one-lesson-per-module seeds.

MODULES = [
    {
        "title": "Why Email Still Sells",
        "lessons": [
            ("The channel you actually own", """
<h2>Rented attention vs. an owned audience</h2>
<p>Most Nigerian businesses sell through channels they don't control: an Instagram page, a Facebook group, a WhatsApp status. These work — until the algorithm changes, the account is restricted, or a group admin removes you. Every follower you have there is <em>rented</em>. The platform decides who sees your post, and increasingly it charges you to reach the people who already chose to follow you.</p>
<p>An email list is different. When someone gives you their email address, you can reach them directly, whenever you choose, at almost no cost per message. No algorithm stands between you and them. If a social account disappears tomorrow, a business with a list can still announce a new product the same afternoon.</p>
<h2>What email is good at</h2>
<ul>
<li><strong>Depth.</strong> A status disappears in 24 hours; an email can explain an offer properly and sit in the inbox until the reader is ready.</li>
<li><strong>Automation.</strong> A sequence of emails can welcome, teach, and follow up with every new subscriber the same way, every time, without you typing anything.</li>
<li><strong>Measurement.</strong> You can see who clicked what, and use that to decide what to send each person next.</li>
</ul>
<h2>The Xpress Selling System in one sentence</h2>
<p>This course teaches you to build a set of automated email sequences that move a stranger from <em>first contact</em> to <em>trusting subscriber</em> to <em>paying customer</em> to <em>repeat customer</em> — and that win back the people who go quiet. You set it up once, then improve it. The goal is not to send more emails. It is to send the right email to the right person at the right time, automatically.</p>
"""),
            ("The three traps most businesses fall into", """
<h2>Trap 1: The broadcast blast</h2>
<p>The business builds a list, then sends the exact same promotional email to everyone, every time. No welcome, no sequence, no attention to what each person is interested in. Results are poor, so the owner concludes email "doesn't work for us".</p>
<h2>Trap 2: One-and-done</h2>
<p>One email goes out, a handful of people respond, and the owner gives up. But very few people buy on first contact, especially from a business they've just discovered. Trust is built over several touches — a useful tip, a story, a testimonial, an offer, a reminder. A single email isn't a strategy; it's a lottery ticket.</p>
<h2>Trap 3: The subscriber desert</h2>
<p>People sign up for a free checklist or a webinar, and then hear nothing for weeks. By the time the business finally sends a sales email, the subscriber has forgotten who they are — and may report the email as spam.</p>
<h2>The fix: treat email as a relationship</h2>
<p>Every trap comes from treating email as a loudspeaker. The Xpress Selling System treats it as a relationship with a purpose for every message, sent according to where each person is in their journey with you. The rest of this course builds that relationship machine one phase at a time.</p>
"""),
            ("Email and WhatsApp: partners, not rivals", """
<h2>Why Nigerian buyers still want WhatsApp</h2>
<p>Many Nigerian buyers trust a conversation more than a form. They want to ask a question, confirm you're real, or negotiate. Pretending email can replace that is a mistake — and so is relying on WhatsApp alone, because broadcast messages there are easy to ignore, hard to automate well, and can get your number reported or banned if you message people who didn't ask.</p>
<h2>Give each channel its job</h2>
<ul>
<li><strong>Email</strong> does the teaching, the trust-building and the structured offers — automatically, at scale.</li>
<li><strong>WhatsApp</strong> handles the human conversation: questions, bookings, support, and closing a buyer who is nearly ready.</li>
</ul>
<p>In practice, many of your emails should end with a clear option to <em>"Chat with us on WhatsApp"</em> using a click-to-chat link (wa.me/234XXXXXXXXXX). The email warms the person up; the chat closes the deal.</p>
<h2>Write for the phone</h2>
<p>Most of your subscribers will read your emails on a phone, often on limited data. That shapes everything in this course: short paragraphs, one clear call to action, light images, and prices shown in naira.</p>
"""),
        ],
        "quiz": [
            ("Why is an email list described as an \"owned\" audience while social media followers are \"rented\"?",
             "On social platforms the algorithm and the platform's rules decide who sees you; with a list you can reach subscribers directly whenever you choose.",
             "You can reach your list directly without a platform's algorithm deciding who sees your message",
             ["Email addresses are legally your property and can be sold",
              "Social media followers cannot buy products online",
              "Email platforms never charge any fees"]),
            ("A business sends one promotional email, gets two replies, and decides email doesn't work. Which trap is this?",
             "One-and-done: most people need several touches before buying, so judging email on a single message is a mistake.",
             "The one-and-done trap",
             ["The broadcast blast trap", "The subscriber desert trap", "The segmentation trap"]),
            ("According to the course, what is the best way to combine email and WhatsApp?",
             "Email handles teaching, trust and structured offers automatically; WhatsApp handles the human conversation and closing.",
             "Email teaches and builds trust automatically; WhatsApp handles questions and closing",
             ["Use only WhatsApp broadcasts because Nigerians don't read email",
              "Use only email and never share a WhatsApp contact",
              "Copy every email word-for-word into WhatsApp broadcasts"]),
        ],
    },
    {
        "title": "Setting Up Properly: Tools, Deliverability and the Law",
        "lessons": [
            ("Choosing an email platform", """
<h2>What you actually need</h2>
<p>You need an email marketing platform (sometimes called an email service provider) that can: host signup forms or landing pages, store contacts with <strong>tags</strong>, send <strong>automations</strong> (sequences triggered by an action such as signing up or buying), and show you basic reports. Do not send marketing email from your personal Gmail — it isn't built for it, you can't automate properly, and you risk your account.</p>
<h2>Common choices</h2>
<ul>
<li><strong>Brevo</strong> (formerly Sendinblue) — generous contact allowance on its free plan, with automations and transactional email.</li>
<li><strong>MailerLite</strong> — simple, clean editor with landing pages and automations; popular with small businesses.</li>
<li><strong>Mailchimp</strong> — widely known, with many integrations; its free plan has become more limited over time.</li>
<li><strong>Kit</strong> (formerly ConvertKit) — built around creators and tag-based automation.</li>
</ul>
<p>Free-plan limits and prices change regularly, so check each platform's current pricing page before deciding. For most small Nigerian businesses starting out, any of the first two is enough. Pick one, and stop comparing — the system matters far more than the tool.</p>
<h2>Paying for it</h2>
<p>Most platforms bill in US dollars. If you upgrade later, confirm that your card works for international subscriptions, and budget for exchange-rate changes.</p>
"""),
            ("Getting into the inbox, not spam", """
<h2>Deliverability is a reputation game</h2>
<p>Gmail, Yahoo and Outlook decide whether your email lands in the inbox, the Promotions tab, or spam. They judge you on whether you are who you say you are, and whether people want your emails.</p>
<h2>Prove who you are: send from your own domain</h2>
<p>Send from an address on your own domain (for example, hello@yourbusiness.com.ng), not from a free @gmail.com address. Your platform will walk you through adding three DNS records at your domain registrar:</p>
<ul>
<li><strong>SPF</strong> — lists which servers are allowed to send email for your domain.</li>
<li><strong>DKIM</strong> — adds a digital signature showing the email wasn't altered.</li>
<li><strong>DMARC</strong> — tells inbox providers what to do with email that fails those checks.</li>
</ul>
<p>Since 2024, Gmail and Yahoo require bulk senders to authenticate their domain, include an easy one-click unsubscribe, and keep spam complaints low. Setting these up properly on day one avoids a lot of pain later.</p>
<h2>Prove people want you</h2>
<ul>
<li>Only email people who asked to hear from you. <strong>Never buy or scrape email lists</strong> — it destroys your sender reputation and may break the law.</li>
<li>Make unsubscribing easy. An unsubscribe is far better for you than a spam complaint.</li>
<li>Remove people who never open or click (Module 7 covers how).</li>
<li>Ask new subscribers to reply to your first email or move it to their main inbox — replies are a strong positive signal.</li>
</ul>
"""),
            ("Consent and the Nigeria Data Protection Act", """
<h2>Personal data comes with legal duties</h2>
<p>An email address, name and phone number are personal data. In Nigeria, the <strong>Nigeria Data Protection Act 2023</strong> sets the rules, and the <strong>Nigeria Data Protection Commission (NDPC)</strong> enforces them. If you have subscribers in other countries, their laws may also apply.</p>
<h2>What this means in practice</h2>
<ul>
<li><strong>Clear consent.</strong> Your signup form should say plainly what people are signing up for — for example, <em>"Get the free checklist and weekly tips by email. Unsubscribe any time."</em> Don't hide it, and don't pre-tick boxes.</li>
<li><strong>Use data only for what you said.</strong> Someone who downloaded a free guide agreed to your emails — not to be added to someone else's list or sold to a third party.</li>
<li><strong>Easy opt-out.</strong> Every marketing email needs a working unsubscribe link, and you must honour it.</li>
<li><strong>Keep it secure.</strong> Use strong passwords and two-factor authentication on your email platform account. Don't download your list into random spreadsheets shared on WhatsApp.</li>
<li><strong>Privacy notice.</strong> Have a simple privacy notice on your website explaining what you collect and why.</li>
</ul>
<p>This lesson is practical guidance, not legal advice. If your business handles large volumes or sensitive data, take proper legal advice on your obligations.</p>
"""),
        ],
        "quiz": [
            ("Which three DNS records prove to inbox providers that your email genuinely comes from your domain?",
             "SPF, DKIM and DMARC are the standard sender-authentication records; Gmail and Yahoo require them for bulk senders.",
             "SPF, DKIM and DMARC",
             ["HTML, CSS and JavaScript", "MX, CNAME and A records only", "SSL, HTTPS and TLS"]),
            ("Why should you never buy an email list?",
             "Bought lists are full of people who never consented — they complain, damage your sender reputation, and may put you in breach of data protection law.",
             "The people never consented, so it damages deliverability and may breach data protection law",
             ["Bought lists are always too small to be useful",
              "Email platforms can't import contacts from files",
              "It is fine as long as the list is Nigerian"]),
            ("Which law sets the rules for handling subscribers' personal data in Nigeria?",
             "The Nigeria Data Protection Act 2023, enforced by the Nigeria Data Protection Commission (NDPC).",
             "The Nigeria Data Protection Act 2023",
             ["The Companies and Allied Matters Act only",
              "There is no data protection law in Nigeria",
              "The Cybercrimes Act forbids all email marketing"]),
        ],
    },
    {
        "title": "Building Your List With Lead Magnets",
        "lessons": [
            ("What makes a great lead magnet", """
<h2>The entry point to your whole system</h2>
<p>A lead magnet is a free, genuinely useful resource you give in exchange for an email address. It decides <em>who</em> joins your list. A vague lead magnet ("Subscribe to our newsletter") brings a thin, uninterested list. A sharp one brings exactly the people who are likely to buy from you.</p>
<h2>The lead magnet checklist</h2>
<ul>
<li><strong>Specific problem:</strong> it solves one problem for one type of person. Not "business tips", but "How to price your catering jobs so you never lose money".</li>
<li><strong>Immediate value:</strong> useful the moment they open it — no long setup.</li>
<li><strong>Quick to consume:</strong> usable in under 30 minutes. A checklist, template, short guide, short video or calculator beats a 100-page ebook.</li>
<li><strong>Directly related to what you sell:</strong> if your lead magnet is about topic A, your paid offer should be the natural next step in topic A.</li>
<li><strong>Easy to deliver:</strong> a PDF, template file or video link that your platform sends automatically.</li>
<li><strong>Clear title:</strong> says exactly who it's for and what it fixes.</li>
<li><strong>Credible:</strong> your name, logo and a short line on why you're qualified.</li>
</ul>
<h2>Examples for Nigerian businesses</h2>
<ul>
<li>A poultry consultant: <em>"Day-Old Chick Brooding Checklist: 15 Things to Prepare Before Your Birds Arrive"</em></li>
<li>A web designer: <em>"The 10-Point Website Audit for Nigerian SMEs"</em></li>
<li>A tutor: <em>"WAEC Mathematics: 30 Past-Question Patterns That Keep Repeating"</em></li>
<li>An accountant: <em>"Small Business Tax Calendar: Every Deadline in One Page"</em></li>
</ul>
"""),
            ("Signup pages and where to put your forms", """
<h2>The landing page</h2>
<p>A lead magnet needs a simple page with one job: get the email address. Keep it to a clear headline (the result they get), three or four bullet points of what's inside, an image of the resource, a short form (name and email is enough), and one button. Remove the menu and other links — every extra link is an exit.</p>
<p>Your email platform can usually build this page for you, or you can use your website.</p>
<h2>Where to put signup forms</h2>
<ul>
<li>Your website homepage, and at the end of every blog post or article.</li>
<li>The link in your Instagram, TikTok, Facebook and X bios.</li>
<li>Your WhatsApp Business profile and catalogue description.</li>
<li>Your email signature.</li>
<li>Pinned posts in groups you run — following each group's rules.</li>
<li>On printed materials and at events, using a QR code that opens the signup page.</li>
</ul>
<h2>Deliver immediately</h2>
<p>Set up an automation that sends the lead magnet the moment someone signs up. Then test it yourself with a personal email address: sign up, confirm it arrives, and click every link. Never assume it works.</p>
"""),
            ("Growing the list week by week", """
<h2>Promote the lead magnet, not "my newsletter"</h2>
<p>Nobody wants a newsletter. People want a solution. When you post on social media, talk about the problem your lead magnet solves and offer it free — "Comment or click the link in my bio for the checklist".</p>
<h2>Simple, honest growth tactics</h2>
<ul>
<li><strong>Content that points to the magnet:</strong> a short video or post that teaches one part of the topic, then offers the full checklist.</li>
<li><strong>Partnerships:</strong> swap mentions with a non-competing business that serves the same customers.</li>
<li><strong>Webinars and live sessions:</strong> registration collects emails, and the replay goes by email.</li>
<li><strong>Existing customers:</strong> ask past buyers if they'd like to receive your tips and offers — with their permission.</li>
</ul>
<h2>Set a realistic target</h2>
<p>For a small business starting from zero, 50 to 100 genuinely interested subscribers in the first month is a good start. A list of 300 people who want what you sell beats 5,000 people who don't remember signing up.</p>
"""),
        ],
        "quiz": [
            ("Which of these is the strongest lead magnet for a catering business?",
             "It solves one specific problem for one type of person, is quick to use, and connects directly to the catering service.",
             "\"How to Price Catering Jobs So You Never Lose Money\" — a one-page calculator",
             ["\"Subscribe to our newsletter\"",
              "A 200-page general business ebook",
              "\"Business tips for everyone\""]),
            ("Why should a lead-magnet landing page usually have no menu or extra links?",
             "The page has one job — collecting the email address — and every extra link is a way for the visitor to leave without signing up.",
             "Every extra link is an exit; the page has one job — collecting the email",
             ["Menus are illegal on landing pages",
              "Email platforms don't allow links",
              "It makes the page load slower than a website"]),
            ("What should you do immediately after setting up the lead-magnet delivery automation?",
             "Test it yourself with a personal address — confirm the email arrives and every link works.",
             "Sign up with a personal email address and check the email arrives and every link works",
             ["Send it to your whole list without testing",
              "Wait a month to see if anyone complains",
              "Nothing — automations always work first time"]),
        ],
    },
    {
        "title": "Phase 1 — Indoctrinate: The Welcome Series",
        "lessons": [
            ("The most valuable window you have", """
<h2>Peak interest</h2>
<p>The moment someone subscribes is when they're most interested in you. They just chose to hear from you. Most businesses waste this window by sending nothing, or one dry "Thanks for subscribing". Phase 1 — <strong>Indoctrinate</strong> — uses it to build trust fast.</p>
<h2>The four questions every new subscriber has</h2>
<ul>
<li>Who are you, and why should I care?</li>
<li>What can I expect from you?</li>
<li>How often will you contact me?</li>
<li>What do you want me to do next?</li>
</ul>
<p>Your welcome series answers all four, in 3 to 5 emails over the first 5 to 7 days, sent automatically to every new subscriber.</p>
<h2>Tone matters</h2>
<p>In Nigeria, a warm, personal tone works far better than stiff corporate copy. Write as if you're writing to one person you genuinely want to help. Use "you" more than "we". Sign off with a real name.</p>
"""),
            ("The 5-email welcome sequence", """
<h2>Email 1 — The welcome (immediately)</h2>
<p>Deliver what they signed up for (the lead magnet link, right at the top). Introduce yourself in two or three human sentences. Say what to expect and how often. Ask them to reply with one word — for example, "Reply and tell me your biggest challenge with X" — which helps deliverability and tells you what they need. Tease what's coming next.</p>
<h2>Email 2 — Your best content (day 2)</h2>
<p>Give something genuinely useful: a how-to, a common mistake and its fix, a short case example. This proves you deliver on your promises. End by teasing the next email.</p>
<h2>Email 3 — Your story (day 4)</h2>
<p>Why do you do this work? What problem made you start? Not a CV — a human story. This is where subscribers start to feel they know you.</p>
<h2>Email 4 — Proof (day 6)</h2>
<p>Share a real client result or testimonial — with their permission. Nigerian buyers are rightly sceptical of online sellers; evidence that you deliver is what moves them. Never invent testimonials.</p>
<h2>Email 5 — The soft offer (day 7)</h2>
<p>Now that they know, like and trust you, make a gentle first offer: an invitation, not a hard sell. Show the price in naira, explain clearly what they get, and give one link — plus the WhatsApp option for questions.</p>
"""),
            ("A worked example: welcome email 1", """
<h2>Example — a poultry consultant</h2>
<p><strong>Subject:</strong> Your brooding checklist is inside 🐣</p>
<blockquote>
<p>Hello Mr Adewale,</p>
<p>Here's your Day-Old Chick Brooding Checklist: <em>[download link]</em></p>
<p>I'm Dr Ngozi. For eight years I've helped farmers across Oyo and Ogun cut early chick deaths. Most losses in the first week come from three avoidable mistakes, and the checklist covers all three.</p>
<p>Over the next week I'll send you a few short emails with the practical things I teach my clients. After that, about one email a week. No noise.</p>
<p>Quick question: how many birds are you raising this cycle? Just hit reply and tell me — I read every answer.</p>
<p>Tomorrow: the brooder temperature mistake that kills more chicks than disease.</p>
<p>Dr Ngozi<br>[Business name] · Chat on WhatsApp: wa.me/234XXXXXXXXXX</p>
</blockquote>
<h2>Why it works</h2>
<ul>
<li>The lead magnet is delivered in the first line.</li>
<li>A short, credible introduction, with no bragging.</li>
<li>Clear expectations on frequency.</li>
<li>A reply request that builds engagement and teaches her about the reader.</li>
<li>An open loop ("Tomorrow: …") that makes email 2 likely to be opened.</li>
</ul>
<p>(The names, business and figures here are an illustration — write from your own real experience.)</p>
"""),
        ],
        "quiz": [
            ("When should a new subscriber receive the lead magnet they signed up for?",
             "Immediately, in the first email — delivering the promise right away builds trust from the first touch.",
             "Immediately, at the top of the first welcome email",
             ["After the third email, to keep them waiting",
              "Only after they buy something",
              "At the end of the month in a newsletter"]),
            ("What is the main job of welcome email 4?",
             "Proof — a real client result or testimonial that shows you deliver, which matters especially to sceptical buyers.",
             "Share real proof — a client result or testimonial, used with permission",
             ["Make a hard, high-pressure sales pitch",
              "Ask them to unsubscribe if not interested",
              "Send a long list of every product you sell"]),
            ("Why does the example welcome email ask the reader to reply?",
             "Replies tell inbox providers people want your mail, and they teach you what your subscribers need.",
             "Replies help deliverability and tell you what the subscriber needs",
             ["To collect their bank details",
              "Because email platforms require a reply to send email 2",
              "To check whether their email address is spelled correctly"]),
        ],
    },
    {
        "title": "Phase 2 — Engage: Turning Subscribers Into Buyers",
        "lessons": [
            ("Gain, Logic and Fear", """
<h2>Selling is a process, not an event</h2>
<p>Phase 2 — <strong>Engage</strong> — is where your system starts making money. The common mistakes are selling too soon (before trust exists) or sending one offer email and giving up.</p>
<h2>The three reasons people decide to buy</h2>
<ul>
<li><strong>Gain</strong> — moving towards something they want. Your email paints a clear picture of the result.</li>
<li><strong>Logic</strong> — justifying the decision. Your email gives facts, what's included, and how the price compares with the cost of the problem.</li>
<li><strong>Fear</strong> — avoiding a loss or missing out. Your email gives an honest reason to act now.</li>
</ul>
<p>Different people respond to different drivers, so a good engagement sequence uses all three, one per email.</p>
<h2>Honest urgency only</h2>
<p>Real deadlines work: an enrolment that closes, a price that genuinely goes up, a limited number of slots you can actually serve. Fake countdowns and "only 2 left" when it isn't true destroy trust the moment people notice — and in Nigeria, where buyers already fear scams, trust is your most valuable asset. If there's no real deadline, use the cost of waiting instead: "Every week you delay is another week of …"</p>
"""),
            ("A 3-email engagement sequence", """
<h2>Email 1 — The gain email</h2>
<p><strong>Subject idea:</strong> How [client] got [result] in [time]</p>
<p>Open with a short story or case example. Show vividly what life looks like after the problem is solved. Keep it warm and conversational, then link to your sales or booking page.</p>
<h2>Email 2 — The logic email</h2>
<p><strong>Subject idea:</strong> Here's why [offer] makes financial sense</p>
<p>Speak to the analytical buyer. Break down exactly what's included. Compare your price with the cost of <em>not</em> solving the problem — lost sales, wasted stock, a failed exam. Add a testimonial or a concrete fact you can stand behind. Answer the two or three questions people always ask.</p>
<h2>Email 3 — The fear email</h2>
<p><strong>Subject idea:</strong> Last chance: [offer] closes [day]</p>
<p>Give a legitimate reason to act now: the real deadline, or the honest cost of waiting. Keep it short. Repeat the link, and offer WhatsApp for anyone with a last question.</p>
<h2>How long should the sequence be?</h2>
<p>Price decides length. For a low-priced offer (a few thousand naira), three emails is often enough. For a high-priced service (hundreds of thousands of naira), expect to need 7 to 10 emails, a call or a chat before people commit — the higher the price, the more trust is needed.</p>
"""),
            ("Running a launch", """
<h2>Automations vs. campaigns</h2>
<p>An <strong>automation</strong> runs for each person when they hit a trigger (they subscribed, they clicked, they bought). A <strong>campaign</strong> (or broadcast) goes to a group on a set date. Your welcome and engagement sequences are automations. A launch — a new product, a seasonal sale, a cohort that opens — is a campaign.</p>
<h2>A simple 6-email launch</h2>
<ul>
<li><strong>Day 1 — Problem:</strong> name the problem and why it matters now.</li>
<li><strong>Day 2 — Story or proof:</strong> a result someone achieved.</li>
<li><strong>Day 3 — Open:</strong> the offer is available; what it is, the price, the link.</li>
<li><strong>Day 4 — Questions:</strong> answer the common objections (price, time, "will it work for me?").</li>
<li><strong>Day 5 — Reminder:</strong> a short nudge with a testimonial.</li>
<li><strong>Day 6 — Closing:</strong> the real deadline is today.</li>
</ul>
<p>Exclude people who have already bought from the remaining launch emails — your platform's tags make this easy — and move them into an onboarding or ascension sequence instead. Promote the launch on social media at the same time to reach people who aren't on the list yet.</p>
"""),
        ],
        "quiz": [
            ("In the Gain–Logic–Fear framework, what is the job of the \"logic\" email?",
             "It speaks to the analytical buyer with facts, what's included and a comparison of the price against the cost of the problem.",
             "Justify the decision with facts, what's included, and price vs. the cost of the problem",
             ["Create a fake countdown timer",
              "Tell a long personal story with no offer",
              "Ask subscribers to forward the email"]),
            ("There is no real deadline on your offer. What does the course recommend for the \"fear\" email?",
             "Never fake urgency. Use the honest cost of waiting, because fake scarcity destroys trust once noticed.",
             "Use the honest cost of waiting instead of inventing a fake deadline",
             ["Invent a deadline anyway — everyone does it",
              "Claim only two slots remain",
              "Skip the offer and never sell"]),
            ("What is the difference between an automation and a campaign?",
             "An automation runs per person when they hit a trigger; a campaign goes to a group on a set date.",
             "An automation runs for each person on a trigger; a campaign goes to a group on a set date",
             ["There is no difference",
              "Automations are only for SMS",
              "Campaigns can only be sent once a year"]),
        ],
    },
    {
        "title": "Phases 3 and 4 — Ascend and Segment",
        "lessons": [
            ("Ascend: sell more to people who already trust you", """
<h2>Your easiest next sale</h2>
<p>The easiest person to sell to is someone who already bought from you. They know you, trust you, and have shown they'll pay. Phase 3 — <strong>Ascend</strong> — makes a relevant follow-on offer after the first purchase. It isn't pushy if the next offer genuinely makes their first purchase more valuable.</p>
<h2>Types of ascension offer</h2>
<ul>
<li><strong>Done-for-you:</strong> they bought a course on building websites; offer to build it for them.</li>
<li><strong>Higher tier:</strong> they bought the basic plan; offer the pro plan.</li>
<li><strong>Retainer:</strong> they paid for a one-off project; offer monthly support and maintenance.</li>
<li><strong>Complementary:</strong> they bought web design; offer copywriting or social media management.</li>
<li><strong>Next level:</strong> they finished the foundation course; offer the intermediate course.</li>
</ul>
<h2>Timing</h2>
<p>First, make sure they get value from what they bought — send an onboarding email or two (how to get started, a quick win). Only then send the ascension offer. A retainer offer the day after you deliver a website, while the client is happy with the result, usually lands far better than one sent three months later.</p>
"""),
            ("Segment: the right message to the right person", """
<h2>Not everyone wants the same thing</h2>
<p>A subscriber interested in broiler farming doesn't want emails about layers. A buyer doesn't want to keep receiving "Buy now!" emails for what they already bought. Phase 4 — <strong>Segment</strong> — means learning what each subscriber wants and routing them to the right sequence automatically.</p>
<h2>Tags are the engine</h2>
<p>Start with three tags: <code>new-subscriber</code>, <code>buyer</code> and <code>non-buyer</code>. Then add interest tags. Every platform supports this (Mailchimp calls them tags and groups, Brevo uses lists and attributes, Kit and MailerLite use tags and groups).</p>
<ul>
<li>Tag buyers automatically when they purchase — and remove them from the sales sequence for that product.</li>
<li>Use a different lead magnet for each main product area, and tag by which one they downloaded.</li>
</ul>
<h2>The hand-raise email</h2>
<p>The simplest segmentation tool: send your list an email asking <em>"Interested in [topic]? Click here and I'll send you more."</em> Everyone who clicks gets tagged and enters the matching engagement sequence automatically.</p>
"""),
            ("The goodwill campaign", """
<h2>Waking up a broadcast list and learning who wants what</h2>
<p>If you already have a list that has only ever received occasional blasts, a goodwill campaign is a good way to restart it. It's three emails a few days apart, each designed to attract a different kind of reader:</p>
<ul>
<li><strong>Email 1 — The teaser:</strong> a short, curiosity-driven email hinting at something valuable. Your most engaged subscribers click.</li>
<li><strong>Email 2 — The direct offer:</strong> a plain description of a specific free resource or offer. Logical readers who want clarity click this one.</li>
<li><strong>Email 3 — The content drop:</strong> a genuinely useful article, video or case study on one topic. Clicks show interest in that topic.</li>
</ul>
<p>Tag everyone who clicks according to what they clicked, then move them into the right engagement sequence. Those who click nothing across all three are candidates for Phase 5.</p>
"""),
        ],
        "quiz": [
            ("When is the best time to send an ascension offer?",
             "After the customer has had a quick win from their first purchase — while they're happy with the result.",
             "After they've had a quick win from their first purchase, while they're happy with it",
             ["Before they've paid for anything",
              "A year later, when they've forgotten you",
              "In the same email as their receipt, before they've used anything"]),
            ("What happens in a \"hand-raise\" email?",
             "You ask the list who is interested in a topic; everyone who clicks is tagged and enters the matching sequence automatically.",
             "Subscribers who click to show interest in a topic are tagged and sent the matching sequence",
             ["Everyone is asked to raise a complaint",
              "All subscribers are deleted except those who reply",
              "You send the same offer to the whole list three times"]),
            ("Why should buyers be tagged automatically when they purchase?",
             "So they stop receiving sales emails for what they already bought and can be moved into onboarding or ascension instead.",
             "So they stop getting sales emails for what they bought and move into onboarding or ascension",
             ["So they can be charged twice",
              "Tags are only for decoration",
              "So they are unsubscribed immediately"]),
        ],
    },
    {
        "title": "Phase 5 — Re-Engage and Keep Your List Healthy",
        "lessons": [
            ("Bringing back the ones who went quiet", """
<h2>Dormant is not gone</h2>
<p>Every list has subscribers who stopped opening and clicking. Some have simply been busy; some changed jobs; some lost interest. Phase 5 — <strong>Re-Engage</strong> — tries to win them back, and cleanly lets go of the ones who don't come back.</p>
<h2>When someone counts as inactive</h2>
<p>A common rule is no clicks for 60 days. Given data costs and patchy connectivity for many Nigerian readers, a slightly longer window — around 90 days — is fairer before you write someone off.</p>
<h2>A one-week re-engagement series</h2>
<ul>
<li><strong>Days 1–3:</strong> send your best content — a genuinely useful resource, no selling.</li>
<li><strong>Days 4–5:</strong> a short, personal email: "I haven't heard from you in a while — are you still interested in [topic]?"</li>
<li><strong>Day 6:</strong> "Should I stop emailing you?" with two clear links: "Yes, keep me on the list" and "No, unsubscribe me". This sounds odd but it works.</li>
<li><strong>Day 7:</strong> remove (or suppress) everyone who still hasn't engaged.</li>
</ul>
"""),
            ("Why a smaller list can earn more", """
<h2>Inactive subscribers cost you</h2>
<p>Inbox providers watch how people treat your email. If a large share of your list ignores you, Gmail and others begin to treat your messages as unwanted and send more of them — even to your keen subscribers — to Promotions or spam. Many platforms also charge by number of contacts, so you pay to email people who never read.</p>
<h2>List hygiene habits</h2>
<ul>
<li>Run the re-engagement series every quarter on newly inactive contacts.</li>
<li>Remove addresses that hard-bounce (they don't exist) — most platforms do this automatically.</li>
<li>Use double opt-in (a confirmation email after signup) if you're seeing lots of fake or mistyped addresses.</li>
<li>Watch your spam-complaint rate in your platform's reports and keep it very low; if it rises, look at what you sent and to whom.</li>
</ul>
<p>A clean list of 800 people who open and click will usually earn more than 5,000 people who don't — and it keeps your emails landing in the inbox.</p>
"""),
        ],
        "quiz": [
            ("Why does the course suggest about 90 days of inactivity, not 60, for many Nigerian subscribers?",
             "Data costs and inconsistent connectivity affect email habits, so a slightly longer window is fairer before writing someone off.",
             "Data costs and patchy connectivity affect reading habits, so a longer window is fairer",
             ["Nigerian law requires exactly 90 days",
              "Email platforms can't measure anything shorter",
              "Inactive subscribers improve deliverability"]),
            ("How do inactive subscribers hurt your business?",
             "Low engagement signals unwanted mail to inbox providers, pushing your email towards spam for everyone, and you may pay per contact.",
             "Low engagement pushes your emails towards spam for everyone, and you may pay per contact",
             ["They don't — a bigger list is always better",
              "They automatically unsubscribe your buyers",
              "They make your emails load more slowly"]),
            ("What should happen on day 7 of the re-engagement series?",
             "Remove or suppress anyone who still hasn't engaged, to protect deliverability.",
             "Remove or suppress everyone who still hasn't engaged",
             ["Send them a hard sales offer every day",
              "Add them to a second list and keep emailing",
              "Sell their addresses to another business"]),
        ],
    },
    {
        "title": "Writing Emails That Get Read and Clicked",
        "lessons": [
            ("The anatomy of an email that converts", """
<h2>Each part has one job</h2>
<ul>
<li><strong>Subject line:</strong> its only job is to get the email opened.</li>
<li><strong>Preview text:</strong> the line shown after the subject in most inboxes — use it to finish the thought, not "View in browser".</li>
<li><strong>Opening line:</strong> hooks the reader with a question, a short story or a surprising point.</li>
<li><strong>Body:</strong> makes one point and leads to the click. Short paragraphs, plain words.</li>
<li><strong>Call to action:</strong> one clear, specific action — "Download the checklist", "Book your free 15-minute call", not "Click here" or five different links.</li>
<li><strong>Landing page:</strong> matches the email. If the email talks about one offer, the page must talk about that same offer.</li>
</ul>
<h2>Write for a phone screen</h2>
<ul>
<li>Paragraphs of one to three lines.</li>
<li>Big, tappable buttons or links.</li>
<li>Few images, and never put the key message only inside an image — many people load emails with images off.</li>
<li>Plain-text-style emails often feel more personal and can perform as well as designed ones — test both.</li>
</ul>
"""),
            ("Subject lines that work", """
<h2>Five types that consistently work</h2>
<ul>
<li><strong>Curiosity:</strong> "What happened when we stopped posting on Instagram"</li>
<li><strong>Direct benefit:</strong> "How to get your first 100 subscribers in 30 days"</li>
<li><strong>Proof:</strong> "How Chuka's agency went from 2 to 12 retainer clients"</li>
<li><strong>Urgency (only when true):</strong> "Closing tonight: [offer]"</li>
<li><strong>Relevance:</strong> "What the new [regulation/season/policy] means for your [business]"</li>
</ul>
<h2>Fill-in-the-blank templates</h2>
<ul>
<li>The [number]-minute fix for [problem]</li>
<li>Are you making this [topic] mistake?</li>
<li>[Number] things I wish I knew before [task]</li>
<li>Step by step: [desired result]</li>
<li>Still struggling with [problem]?</li>
<li>What [successful group] know about [topic] that you don't</li>
<li>The real cost of not fixing [problem]</li>
<li>Quick question about [their goal]</li>
<li>New: [resource] for [specific audience]</li>
<li>Your [checklist/guide] is inside</li>
<li>[First name], did you see this?</li>
<li>Before you spend another naira on [thing]…</li>
</ul>
<h2>Avoid</h2>
<p>ALL CAPS, piles of exclamation marks, misleading "RE:" or "FWD:" prefixes, and clickbait that the email doesn't deliver on. They hurt trust and can trigger spam filters.</p>
"""),
            ("Testing what works", """
<h2>A/B testing subject lines</h2>
<p>For important emails, most platforms let you test two subject lines. A common approach: send version A to 20% of the list and version B to another 20%, wait a few hours, then send the winner to the remaining 60%. Over time, this habit teaches you what your own audience responds to — which matters more than any general rule.</p>
<h2>Test one thing at a time</h2>
<p>Test the subject line, <em>or</em> the call to action, <em>or</em> the send time — not all at once, or you won't know what made the difference. Small lists give noisy results, so look for consistent patterns over several sends rather than trusting a single test.</p>
"""),
        ],
        "quiz": [
            ("What is the only job of a subject line?",
             "To get the email opened. The body's job is the click; the landing page's job is the sale or signup.",
             "To get the email opened",
             ["To close the sale on its own",
              "To include every keyword about your business",
              "To show your logo"]),
            ("Why shouldn't the key message of an email appear only inside an image?",
             "Many people load email with images off or on slow data, so a message trapped in an image may never be seen.",
             "Many readers have images off or slow data, so they may never see it",
             ["Images are banned in marketing emails",
              "Images always go to spam",
              "Text inside images is easier to read on phones"]),
            ("When A/B testing, why should you test one thing at a time?",
             "If you change several things at once, you can't tell which change caused the difference.",
             "Otherwise you can't tell which change made the difference",
             ["Platforms only allow one test per year",
              "Testing two things doubles the cost of every email",
              "It doesn't matter how many things you change"]),
        ],
    },
    {
        "title": "Measuring Results and Your 30-Day Launch Plan",
        "lessons": [
            ("The numbers that matter", """
<h2>Read your reports properly</h2>
<ul>
<li><strong>Open rate:</strong> useful as a rough trend only. Apple Mail Privacy Protection and image blocking make opens unreliable — many "opens" are automatic, and some real opens aren't counted. Don't make big decisions on opens alone.</li>
<li><strong>Click rate:</strong> the share of recipients who clicked a link — a much more honest signal of interest.</li>
<li><strong>Conversion:</strong> how many clickers did the thing you wanted — signed up, booked, paid. This is the number that pays the bills; track it with your payment platform or a simple spreadsheet.</li>
<li><strong>Unsubscribes and spam complaints:</strong> a few unsubscribes after each email is normal and healthy. A rise in spam complaints is a warning sign.</li>
<li><strong>List growth:</strong> new subscribers minus unsubscribes and removals, each month.</li>
</ul>
<h2>Revenue per subscriber</h2>
<p>Divide the money your emails brought in over a period by the number of subscribers. It tells you what a new subscriber is worth to you — and therefore how much effort or ad spend it's sensible to put into growing the list.</p>
<h2>Improve one piece at a time</h2>
<p>Each month, find the weakest link: is it signups, the welcome series, clicks on the offer, or the sales page? Fix that one thing, measure again, repeat.</p>
"""),
            ("Your 30-day quick-start plan", """
<h2>Week 1 — Foundation</h2>
<ul>
<li>Choose your email platform and create the account (with two-factor authentication).</li>
<li>Set up sending from your own domain with SPF, DKIM and DMARC.</li>
<li>Decide your lead magnet: one specific problem, one type of person.</li>
<li>Create it — aim for a first draft within 48 hours, then design a clean cover.</li>
</ul>
<h2>Week 2 — Capture and welcome</h2>
<ul>
<li>Build the landing page and connect it to your platform.</li>
<li>Write and schedule the 5-email welcome series.</li>
<li>Test the whole flow with your own email address — every link.</li>
<li>Add the signup link to your bios, website, WhatsApp Business profile and email signature.</li>
</ul>
<h2>Week 3 — Engage</h2>
<ul>
<li>Write the 3-email engagement sequence (gain, logic, fear) for your main offer.</li>
<li>Set up the <code>buyer</code> tag so buyers leave the sales sequence automatically.</li>
<li>Promote the lead magnet daily on your social channels.</li>
</ul>
<h2>Week 4 — Review and optimise</h2>
<ul>
<li>Check clicks and conversions; find which welcome email gets the most clicks and why.</li>
<li>A/B test the subject line of your most important email.</li>
<li>Plan your first segmentation (hand-raise) email and an ascension offer for buyers.</li>
</ul>
<p>After 30 days you'll have a working system: a lead magnet bringing in the right people, a welcome series building trust, and an engagement sequence turning subscribers into buyers — running every day without you. From here, keep improving one piece at a time.</p>
"""),
        ],
        "quiz": [
            ("Why should open rates be treated only as a rough trend?",
             "Privacy features such as Apple Mail Privacy Protection and image blocking make opens unreliable in both directions.",
             "Privacy features and image blocking make opens unreliable",
             ["Open rates are always exactly accurate",
              "Platforms no longer show open rates at all",
              "Opens are the only number that matters"]),
            ("Which metric most directly shows whether your emails make money?",
             "Conversion — how many people completed the purchase, booking or signup you wanted.",
             "Conversion — how many people bought, booked or signed up",
             ["Number of emails sent", "Number of images used", "Length of the subject line"]),
            ("In the 30-day plan, what should you do right after writing the welcome series?",
             "Test the whole flow yourself with a personal email address, checking every link.",
             "Test the full flow with your own email address and check every link",
             ["Delete it and start again",
              "Buy a list to send it to",
              "Wait three months before switching it on"]),
        ],
    },
]

FINAL_EXAM_QUESTIONS = [
    ("What are the five phases of the Xpress Selling System, in order?",
     "Indoctrinate (welcome), Engage (first sale), Ascend (sell more to buyers), Segment (right message to the right person), Re-Engage (win back the quiet ones).",
     "Indoctrinate, Engage, Ascend, Segment, Re-Engage",
     ["Attract, Blast, Close, Delete, Repeat",
      "Segment, Indoctrinate, Re-Engage, Engage, Ascend",
      "Welcome, Discount, Discount, Discount, Unsubscribe"]),
    ("What is the core goal of the system, as stated in the course?",
     "Not more email — the right email to the right person at the right time, automatically.",
     "To send the right email to the right person at the right time, automatically",
     ["To send as many emails as possible every day",
      "To replace WhatsApp completely",
      "To email the whole list the same offer every week"]),
    ("Which is the clearest example of the \"subscriber desert\" trap?",
     "Collecting emails and then sending nothing for weeks, so subscribers forget who you are.",
     "People sign up for a free guide, then hear nothing for weeks",
     ["Sending one email and giving up",
      "Sending the same blast to everyone",
      "Sending a welcome series immediately"]),
    ("Why should you send marketing email from your own domain rather than a free Gmail address?",
     "Your own domain can be authenticated with SPF, DKIM and DMARC, which inbox providers require of bulk senders and which protects deliverability.",
     "Your own domain can be authenticated (SPF, DKIM, DMARC), which protects deliverability",
     ["Gmail addresses cannot send email to Nigerian users",
      "Domains make emails arrive faster",
      "It is purely about looking fancy"]),
    ("Which signup-form wording best meets the consent principles of the Nigeria Data Protection Act?",
     "It says plainly what the person is signing up for and that they can leave at any time.",
     "\"Get the free checklist and weekly tips by email. Unsubscribe any time.\"",
     ["A pre-ticked box hidden at the bottom of the page",
      "No wording — just collect the email",
      "\"By visiting this site you agree to receive all our partners' emails\""]),
    ("Which lead magnet best meets the checklist criteria?",
     "It is specific, quick to use, immediately valuable, and leads naturally to a related paid service.",
     "A one-page tax deadline calendar for small business owners, from an accountant",
     ["A 150-page general ebook about everything in business",
      "\"Join our newsletter\"",
      "A free phone, unrelated to what the business sells"]),
    ("In the welcome series, what is the purpose of the \"your story\" email?",
     "It helps subscribers feel they know you by sharing why you do this work — a human story, not a CV.",
     "To help subscribers feel they know you by sharing why you do this work",
     ["To list every qualification you've ever earned",
      "To make the hardest sales pitch of the series",
      "To ask for referrals before they trust you"]),
    ("A business offers a ₦350,000 consulting package. Compared with a ₦3,000 ebook, what should its engagement sequence look like?",
     "Higher prices need more trust, so expect a longer sequence (often 7–10 emails) plus a call or chat.",
     "Longer — often 7 to 10 emails plus a call or chat, because higher prices need more trust",
     ["Exactly the same three emails",
      "A single email with the price",
      "No emails at all — only cold calls"]),
    ("Which use of urgency is acceptable under the course's principles?",
     "Only real deadlines or real limits; fake scarcity destroys trust when discovered.",
     "\"Enrolment closes Friday at midnight\" — when it genuinely does",
     ["A countdown timer that restarts every time the page loads",
      "\"Only 2 slots left\" when there is no limit",
      "Claiming the price rises tomorrow when it doesn't"]),
    ("A web designer has just delivered a ₦150,000 website to a happy client. What ascension offer does the course suggest?",
     "A monthly retainer for support and updates is a natural, genuinely useful next step for a delivered project.",
     "A monthly support-and-updates retainer, offered soon after delivery",
     ["A second identical website",
      "Nothing — never sell to existing clients",
      "A discount on the website they already paid for"]),
    ("What should happen when a subscriber buys the product an engagement sequence is selling?",
     "They're tagged as a buyer, removed from that sales sequence, and moved into onboarding or ascension.",
     "They are tagged as a buyer, leave that sales sequence and move to onboarding or ascension",
     ["They keep receiving \"Buy now\" emails for it",
      "They are unsubscribed from everything",
      "Nothing changes"]),
    ("In a goodwill campaign, what do the clicks on each of the three emails tell you?",
     "Who is engaged and which topics or offers interest them, so you can tag them and route them to the right sequence.",
     "Who is engaged and what they're interested in, so you can tag and route them",
     ["Nothing useful",
      "Which subscribers to charge extra",
      "Which subscribers want to be unsubscribed"]),
    ("Why can removing inactive subscribers increase your email results?",
     "Low engagement tells inbox providers your mail is unwanted, pushing it to spam for everyone; a clean, engaged list lands in the inbox.",
     "An engaged list keeps your mail landing in the inbox for everyone",
     ["Removing contacts always doubles your sales immediately",
      "Inactive subscribers delete your emails from other people's inboxes",
      "Platforms only deliver to lists under 500 people"]),
    ("Which call to action is strongest?",
     "It is specific, says exactly what happens next, and stands alone as the one action in the email.",
     "\"Book your free 15-minute call\" as the single clear button",
     ["\"Click here\" repeated five times with different links",
      "No link — they'll find you",
      "A list of all ten of your products"]),
    ("A plain-text email gets more clicks than your designed one across several sends. What does this tell you?",
     "Your own audience's behaviour over several tests is the best guide; keep using what consistently works for them.",
     "Your audience responds better to plain text — use the consistent pattern from your own tests",
     ["Testing is pointless",
      "Designed emails are illegal",
      "One send proves everything forever"]),
    ("Why is click rate a more trustworthy measure than open rate?",
     "Privacy features make opens unreliable, while a click is a deliberate action showing real interest.",
     "A click is a deliberate action, while opens are distorted by privacy features",
     ["Clicks are always higher than opens",
      "Open rates are no longer reported",
      "Click rate includes people who never received the email"]),
]


class Command(BaseCommand):
    help = (
        "Seeds 'The Xpress Selling System' — email marketing and automation "
        "for Nigerian businesses, rebuilt from the Xpress Digital store's "
        "ebooks. Several lessons and a quiz per module, plus a final exam. "
        "Created unpublished. Safe to re-run."
    )

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        programme, _ = Programme.objects.get_or_create(
            organization=org, slug="business-and-entrepreneurship",
            defaults={
                "title": "Business & Entrepreneurship",
                "audience": Audience.GENERAL,
                "description": "Practical, deep business-management courses for Nigerian entrepreneurs and SME owners.",
            },
        )

        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                organization=org, programme=programme, slug="xpress-selling-system",
                defaults={
                    "title": "The Xpress Selling System: Email Marketing That Sells While You Sleep",
                    "subtitle": "Build automated email sequences that turn strangers into paying, repeat "
                                "customers — set up step by step for Nigerian businesses.",
                    "description": "<p>A practical course on building an email selling system for a Nigerian "
                                   "business. You'll set up the right tools, get into the inbox (SPF, DKIM, DMARC), "
                                   "collect emails lawfully under the Nigeria Data Protection Act, and build lead "
                                   "magnets that attract real buyers. Then you'll build the five phases of the "
                                   "Xpress Selling System: a welcome series that builds trust, an engagement "
                                   "sequence that makes the first sale, ascension offers for existing customers, "
                                   "segmentation with tags, and re-engagement for subscribers who go quiet. It "
                                   "finishes with writing emails that get read, measuring what matters, and a "
                                   "30-day plan to launch.</p>",
                    "audience": Audience.GENERAL,
                    "level": Course.Level.FOUNDATION,
                    "pricing_model": Course.PricingModel.PAID,
                    "price_ngn": 5000,
                    "access_type": Course.AccessType.LIFETIME,
                    "requires_final_assessment": True,
                    "estimated_hours": 4.0,
                    "is_published": False,
                    "sales_headline": "Sell while you sleep — with email that builds trust first",
                    "sales_subheadline": "Nine practical modules: tools, deliverability, the law, lead magnets, "
                                         "and the five-phase Xpress Selling System — with Nigerian examples, "
                                         "templates and a 30-day launch plan.",
                    "target_audience": (
                        "Business owners tired of chasing every sale by hand on WhatsApp and Instagram\n"
                        "Consultants, coaches, tutors and service providers who want a steady flow of clients\n"
                        "Anyone selling digital products, courses or services online in Nigeria"
                    ),
                    "not_for": (
                        "People looking for bulk SMS or spam tools — this course is about permission-based "
                        "email that people asked for"
                    ),
                    "instructor_bio": "Dr. Omale Ojonimi Samuel, Founder, Xpress Digital & Data Solutions Limited.",
                    "meta_description": "Email marketing for Nigerian businesses: lead magnets, welcome series, "
                                        "sales sequences, segmentation and a 30-day plan to launch.",
                },
            )

            if not created:
                self.stdout.write(self.style.WARNING(f"{course.title} already exists — leaving as-is."))
                return

            self.stdout.write(self.style.SUCCESS(f"Created course: {course}"))
            lesson_count = 0
            for i, spec in enumerate(MODULES, start=1):
                module = Module.objects.create(
                    course=course, order=i, title=spec["title"], unlock_rule=Module.UnlockRule.SEQUENTIAL,
                )
                for j, (title, body) in enumerate(spec["lessons"], start=1):
                    Lesson.objects.create(
                        module=module, order=j, title=title, type=Lesson.Type.TEXT,
                        body=body.strip(), is_preview=(i == 1),
                    )
                    lesson_count += 1

                bank = QuestionBank.objects.create(
                    organization=org, name=f"Xpress Selling System — Module {i} quiz",
                    description=spec["title"],
                )
                self._add_questions(bank, spec["quiz"])
                Quiz.objects.create(
                    scope=Quiz.Scope.MODULE, module=module, title=f"Module {i} quiz",
                    instructions=f"{len(spec['quiz'])} quick questions on this module.",
                    bank=bank, question_count=len(spec["quiz"]), pass_mark=60,
                    max_attempts=0, time_limit_minutes=0,
                )
            self.stdout.write(self.style.SUCCESS(
                f"  {len(MODULES)} modules, {lesson_count} lessons, {len(MODULES)} module quizzes."
            ))

            bank = QuestionBank.objects.create(
                organization=org, name="Xpress Selling System — Final Exam",
                description="Covers all modules — must be passed to unlock the certificate.",
            )
            self._add_questions(bank, FINAL_EXAM_QUESTIONS)
            Quiz.objects.create(
                scope=Quiz.Scope.FINAL, course=course, title="Final Exam — The Xpress Selling System",
                instructions=f"{len(FINAL_EXAM_QUESTIONS)} questions covering the full course. "
                             "Pass to unlock your certificate.",
                bank=bank, question_count=len(FINAL_EXAM_QUESTIONS), pass_mark=70,
                max_attempts=0, time_limit_minutes=0,
            )
            self.stdout.write(self.style.SUCCESS("Created the final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. Course is unpublished — review, set Vertical + Approved + is_published in admin."
        ))

    def _add_questions(self, bank, questions):
        for stem, explanation, correct, wrongs in questions:
            q = Question.objects.create(
                bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                difficulty=Question.Difficulty.MEDIUM,
            )
            Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
            for k, wrong in enumerate(wrongs, start=2):
                Choice.objects.create(question=q, text=wrong, is_correct=False, order=k)
