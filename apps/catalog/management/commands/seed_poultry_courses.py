from django.core.management.base import BaseCommand
from django.db import transaction

from apps.assessment.models import Choice, Question, QuestionBank, Quiz
from apps.catalog.models import Audience, Course, Lesson, Module, Programme
from apps.organizations.models import Organization

# A 3-course poultry series for veterinarians — the "Veterinary
# Continuing Education" programme's second track, same audience/
# programme as Canine Reproduction for Practitioners. Same content
# discipline: CE-level conceptual/diagnostic depth, drug classes and
# mechanisms discussed generally rather than specific dosing
# protocols, general knowledge deferred to product literature and
# clinical judgment on anything prescriptive.

COURSE_1_MODULES = [
    ("Flock Health Surveillance and the Poultry-Specific Exam",
     """<h2>Why flock medicine is a different discipline</h2>
<p>Individual-bird physical exam findings matter, but poultry practice is fundamentally population medicine — a single sick bird is often a sentinel for a flock-level problem, and the real diagnostic unit is the flock's aggregate data: mortality curve, feed/water consumption, egg production trend, and behavioral changes across the house, not one bird's clinical signs in isolation.</p>
<h2>Building a surveillance routine</h2>
<p>A structured flock visit reviews daily mortality records (a sudden spike or a slow creep both matter, for different reasons), feed and water consumption trends (often the earliest signal of a developing problem, before clinical signs are visible), and a representative sample of birds examined individually — not just the obviously sick ones, since apparently healthy birds in an affected flock carry real diagnostic information too.</p>
<h2>The poultry physical exam</h2>
<p>Beyond general body condition: comb and wattle color and texture (pale, cyanotic, or necrotic changes all mean something different), respiratory effort and sounds (poultry respiratory disease is common and often the presenting complaint), crop content and consistency, vent and cloacal examination, and gait/leg conformation — lameness is both a welfare issue and frequently a sign of systemic disease.</p>
<h2>Reading production data as a diagnostic tool</h2>
<p>For layers: a drop in egg production or shell quality often precedes obvious clinical signs by days. For broilers: feed conversion ratio drifting off target is frequently the first measurable sign something is wrong, well before mortality rises. Practitioners who read production data as clinical data, not just management data, catch problems earlier.</p>
<h2>Working with farm records</h2>
<p>A good relationship with the farm manager and access to genuinely accurate records (not just what's convenient to report) is the foundation everything else in this course builds on — flock medicine done without real data is guesswork with extra steps.</p>"""),
    ("Biosecurity Program Design",
     """<h2>Biosecurity as the actual first line of defense</h2>
<p>For most poultry diseases covered later in this course, prevention through biosecurity is more effective, and dramatically cheaper, than treatment after an outbreak. A practice that only shows up to treat sick flocks, without ever addressing biosecurity, is treating symptoms of a system problem.</p>
<h2>Structural biosecurity</h2>
<p>Physical separation between the farm and outside traffic (perimeter fencing, controlled entry points), all-in/all-out management where feasible (mixing ages dramatically increases disease transmission risk), and dedicated equipment per house or per farm rather than shared tools moving disease between units.</p>
<h2>Operational biosecurity</h2>
<p>Footwear and clothing changes at entry points, vehicle disinfection protocols for anything entering the farm, visitor logs and genuine restriction (not just a sign-in sheet nobody enforces), and a clear, written protocol for handling mortality removal and disposal — an area commonly under-managed in practice.</p>
<h2>Biosecurity for backyard and small-flock operations</h2>
<p>Commercial-scale protocols don't translate directly to a backyard flock, but the same principles scale down: minimizing contact with wild birds, quarantining new birds before introduction, and basic hygiene at entry points are realistic and worth actively teaching to this client segment, not skipped because "it's just a backyard flock."</p>
<h2>Auditing biosecurity, not just designing it</h2>
<p>A written protocol that isn't actually followed provides no real protection. Periodic, honest biosecurity audits — walking the actual entry points and procedures with the farm manager, not just reviewing the document — are what make a program real rather than aspirational.</p>"""),
    ("Common Viral Diseases: Newcastle, Avian Influenza, IBD, Marek's",
     """<h2>Newcastle disease</h2>
<p>A paramyxovirus causing respiratory, nervous, and/or digestive signs depending on strain virulence — velogenic strains cause high mortality and are a major economic and, in many jurisdictions, reportable-disease concern. Vaccination is central to control in endemic areas; recognizing atypical or vaccine-breakthrough presentations is a real diagnostic skill worth building deliberately.</p>
<h2>Avian influenza</h2>
<p>Low-pathogenic strains may cause mild or subclinical disease; highly pathogenic strains cause severe, rapid mortality and carry major reportable-disease, trade, and — for some subtypes — zoonotic implications. Any sudden, severe, unexplained mortality event in poultry should keep HPAI on the differential list until genuinely ruled out, given the stakes of missing it.</p>
<h2>Infectious bursal disease (Gumboro)</h2>
<p>Targets the bursa of Fabricius, causing direct mortality in acute cases and, significantly, immunosuppression in survivors that predisposes the flock to secondary disease for weeks afterward — a flock that "recovered" from IBD may still be at elevated risk from other pathogens for some time.</p>
<h2>Marek's disease</h2>
<p>A herpesvirus causing lymphoid tumors and nerve involvement (visible as characteristic leg paralysis patterns), controlled almost entirely through in-ovo or day-of-hatch vaccination rather than treatment — there's essentially no effective treatment once clinical disease is established, which makes vaccination program integrity the entire control strategy.</p>
<h2>Building differential-diagnosis discipline</h2>
<p>These four diseases can present with overlapping signs (respiratory involvement, nervous signs, drops in production) — history (vaccination status, recent introductions, regional disease pressure), pattern of spread, and targeted diagnostic sampling (Module 2 of the advanced course in this series) are what actually separate them, not clinical signs alone.</p>"""),
    ("Bacterial and Parasitic Disease in Poultry",
     """<h2>Colibacillosis</h2>
<p>E. coli infection, often secondary to a primary insult (viral disease, poor air quality, stress) rather than a true primary pathogen in most cases — meaning effective control usually means addressing the underlying predisposing factor, not just treating the E. coli itself, or the same flock (or the next one) will likely see it recur.</p>
<h2>Mycoplasma (chronic respiratory disease)</h2>
<p>Causes chronic, often low-grade respiratory disease that reduces production and predisposes to secondary infection — significant in layer and breeder flocks especially, where it can persist and spread vertically through the breeding pyramid if not controlled at that level.</p>
<h2>Salmonella</h2>
<p>Beyond the poultry health concern itself: specific serovars carry real public-health/zoonotic significance and food-safety regulatory implications — control programs here often intersect with food-safety compliance requirements, not purely clinical ones.</p>
<h2>Coccidiosis</h2>
<p>An Eimeria protozoal disease affecting the intestinal tract, historically controlled largely through in-feed anticoccidials and increasingly through live vaccination and management-based approaches as resistance concerns grow — a genuinely evolving area of poultry medicine worth staying current on rather than assuming the historical control approach still fully applies.</p>
<h2>External and internal parasites</h2>
<p>Mites and lice affect welfare and, at high burden, production; internal parasites (various nematodes) are more of a concern in extensive/backyard systems than tightly managed commercial housing — worth calibrating your differential list to the actual production system you're examining.</p>"""),
    ("Vaccination Program Design and Cold Chain Management",
     """<h2>Designing a program, not just picking vaccines</h2>
<p>An effective vaccination program accounts for maternal antibody interference (vaccinating too early against maternal antibody can fail silently), regional disease pressure, production type and lifespan (a broiler's short life needs a very different program than a multi-year layer or breeder), and route/method appropriate to the specific vaccine (in-ovo, spray, drinking water, injection each have real technique requirements).</p>
<h2>The cold chain — the same principle as Module 7 of the breeder-track course, at production scale</h2>
<p>A vaccine that's lost potency through a cold-chain failure produces a program that looks complete on paper but provides no real protection — arguably worse than skipping it, since it creates false confidence. Verifying storage and transport temperature at every handoff point, not just trusting the label, is non-negotiable at this scale.</p>
<h2>Monitoring program effectiveness</h2>
<p>Serology (checking antibody titers post-vaccination) is the real way to confirm a program is actually working, not just assuming it did because the vaccine was administered — periodic titer checks, especially after any program change, close the loop between "we vaccinated" and "the flock is actually protected."</p>
<h2>Route and technique matter as much as vaccine choice</h2>
<p>Spray vaccination with inadequate droplet size or coverage, or drinking-water vaccination with residual disinfectant in the lines killing a live vaccine before birds even drink it, are common real-world failure points — technique audits are as important as program design on paper.</p>
<h2>Adjusting for real-world constraints</h2>
<p>A theoretically ideal program a farm can't actually execute reliably provides less real protection than a slightly simpler program executed consistently — designing for what a specific operation can actually deliver, not just textbook ideal, is part of doing this well.</p>"""),
]

COURSE_2_MODULES = [
    ("Nutritional Requirements Across Production Stages",
     """<h2>Why poultry nutrition is stage-specific</h2>
<p>Nutrient requirements shift meaningfully across a bird's life — starter, grower, finisher for broilers; pullet-rearing through peak and late lay for layers — and a diet appropriate for one stage fed at another wastes money at best and actively harms production or welfare at worst.</p>
<h2>Energy and protein balance</h2>
<p>Poultry diets are formulated around an energy-to-protein ratio, not either nutrient in isolation — too much energy relative to protein drives excess fat deposition (a real welfare and production-efficiency concern in broilers); too little energy relative to protein means birds burn protein for energy, an expensive and inefficient outcome.</p>
<h2>Amino acid balance, not just crude protein</h2>
<p>Modern formulation targets specific amino acids (methionine and lysine especially) rather than crude protein percentage alone — two diets with identical crude protein can perform very differently depending on amino acid balance, a distinction worth understanding even if you're not personally formulating diets.</p>
<h2>Calcium and phosphorus in layers</h2>
<p>Laying hens have dramatically elevated calcium requirements for shell production — inadequate calcium leads to poor shell quality and, over time, skeletal problems as the bird mobilizes bone calcium to meet egg-production demand. Particle size of the calcium source (coarse limestone/oyster shell for sustained release overnight) matters as much as the total amount fed.</p>
<h2>Water — the most overlooked nutrient</h2>
<p>Water intake issues (quality, availability, or palatability) show up as production problems that get misattributed to feed formulation — always worth ruling out water as a genuine root cause before assuming a nutritional or disease explanation for an unexplained production drop.</p>"""),
    ("Feed Formulation and Quality Control",
     """<h2>Working with, not replacing, a nutritionist</h2>
<p>Most practitioners aren't formulating diets from scratch — but understanding formulation well enough to have an informed conversation with a farm's nutritionist, and to recognize when a production problem might actually be a feed issue, is a genuinely valuable skill.</p>
<h2>Ingredient quality and variability</h2>
<p>Feed ingredients (grain, oilseed meals) vary in nutrient content batch to batch — a formulation that's correct on paper can underperform if the actual ingredients used don't match the assumed nutrient values, which is why ongoing ingredient testing matters at real production scale.</p>
<h2>Mycotoxins</h2>
<p>Contaminated grain can carry mycotoxins causing a range of effects from reduced performance to immunosuppression to acute toxicity depending on the toxin and level — worth being on the differential list for unexplained flock-wide performance problems, especially following poor grain storage conditions or a wet harvest season.</p>
<h2>Feed mill hygiene and pelleting quality</h2>
<p>Pellet quality affects intake and feed conversion — excessive fines (broken pellet fragments) are typically less palatable and more wasted. Feed mill sanitation also matters for pathogen control (Salmonella contamination at the mill level is a real, documented risk pathway).</p>
<h2>Recognizing a feed-related production problem</h2>
<p>A sudden, flock-wide production or feed-conversion change with no clinical/disease signs, especially correlating with a feed delivery or ingredient source change, points toward feed rather than disease — a useful pattern-recognition heuristic when building your differential.</p>"""),
    ("Housing, Environment, and Welfare in Commercial Systems",
     """<h2>Ventilation as a health, not just comfort, issue</h2>
<p>Poor ventilation drives ammonia buildup (damaging respiratory tract lining and predisposing to respiratory disease), excess humidity (favoring pathogen survival and litter/bedding quality problems), and temperature stress — ventilation assessment is a genuine clinical skill, not purely a facilities-management concern.</p>
<h2>Litter quality and its downstream effects</h2>
<p>Wet, caked litter drives ammonia production, footpad dermatitis (a real welfare indicator increasingly tracked by buyers/auditors), and creates a favorable environment for pathogen persistence between flocks — litter management is genuinely preventive medicine, not just housekeeping.</p>
<h2>Stocking density</h2>
<p>Density affects welfare directly and also indirectly drives disease transmission risk (more birds in closer contact) and air quality challenges — increasingly regulated and audited in many markets, worth knowing the relevant standards for whatever market/certification a given operation sells into.</p>
<h2>Lighting programs</h2>
<p>Light intensity and photoperiod are actively managed tools, not incidental — layer lighting programs specifically manage the onset and maintenance of lay, and broiler lighting programs balance growth rate against welfare and leg-health outcomes.</p>
<h2>Welfare auditing as a practice service</h2>
<p>Many buyers now require third-party or veterinary welfare audits — a practitioner who understands housing/environment assessment at this level can offer genuine audit/consulting value beyond individual flock treatment, a real practice-growth opportunity covered further in Module 5.</p>"""),
    ("Layer vs Broiler Production — Distinct Management Demands",
     """<h2>Why these are genuinely different disciplines</h2>
<p>A layer is managed for a multi-year production lifespan and egg output; a broiler is managed for maximal growth rate over a matter of weeks. The health priorities, common disease patterns, and even the physical exam emphasis differ meaningfully between them.</p>
<h2>Layer-specific priorities</h2>
<p>Long-term skeletal health (given sustained calcium mobilization for shell production over the laying cycle), reproductive tract health (egg peritonitis, prolapse, and related conditions are layer-specific concerns), and managing the transition through molt where applicable.</p>
<h2>Broiler-specific priorities</h2>
<p>Rapid growth rate creates real skeletal and cardiovascular strain — leg disorders and conditions like ascites (linked to the metabolic demand of fast growth, especially at altitude or with ventilation challenges) are broiler-characteristic concerns rarely seen in layers.</p>
<h2>Breeder flocks — a hybrid case</h2>
<p>Broiler and layer breeder flocks are managed for reproductive output rather than meat or table-egg production directly, adding fertility, hatchability, and vertical-disease-transmission concerns (some pathogens pass through the egg) on top of the priorities of their respective production type.</p>
<h2>Tailoring your clinical approach</h2>
<p>Walking into a broiler house with a layer-flock mental model (or vice versa) means missing the differentials that actually matter for that system — deliberately recalibrating your exam and differential list to the specific production type in front of you is a real, learnable clinical habit.</p>"""),
    ("Production Economics and Record-Keeping",
     """<h2>Why economics literacy makes you a better clinician here</h2>
<p>Poultry medicine decisions are made against real cost/return math the farm is managing daily — understanding feed conversion ratio, mortality cost, and production-value-per-bird lets you frame clinical recommendations in terms that connect to what the farm manager is actually optimizing for.</p>
<h2>Feed conversion ratio (FCR)</h2>
<p>The core broiler efficiency metric — feed consumed per unit of weight gained. Small FCR shifts have large economic impact at commercial scale, which is exactly why FCR drift is often the earliest measurable sign of a developing health problem, well before mortality (Module 1).</p>
<h2>Mortality cost, properly calculated</h2>
<p>Mortality cost isn't just the lost bird — it's lost feed already invested in that bird, lost housing capacity, and at older ages, lost near-term production value. A clear framework for this helps justify preventive investment (biosecurity, vaccination) against its real cost-avoidance value, not just its upfront cost.</p>
<h2>Record systems worth building</h2>
<p>Consistent, accurate daily records (mortality, feed/water consumption, production, treatments given) are the raw material every other module in this course depends on — a practice that helps farms build genuinely reliable record-keeping is investing in its own future diagnostic capability, not just doing the farm a favor.</p>
<h2>Communicating value to the farm</h2>
<p>Framing a health or biosecurity recommendation in terms of its economic return (cost avoided, FCR protected, mortality reduced) rather than purely clinical language is often what actually gets a recommendation implemented — a genuinely practical communication skill worth deliberately building.</p>"""),
]

COURSE_3_MODULES = [
    ("The Systematic Poultry Necropsy",
     """<h2>Why a systematic approach matters more here than in companion animal practice</h2>
<p>A flock-medicine necropsy is often diagnosing on behalf of thousands of birds, not one patient — a systematic, consistent approach that doesn't miss findings matters enormously, and a good necropsy routine is one of the highest-value skills in this whole course.</p>
<h2>External examination first</h2>
<p>Body condition, feather condition, evidence of trauma or external parasites, and vent/cloacal condition — all assessed before the first incision, since some of this evidence is easy to disturb or lose once the internal exam begins.</p>
<h2>A consistent internal sequence</h2>
<p>Most practitioners develop a fixed order (respiratory tract, then digestive tract, then reproductive/urinary, then musculoskeletal/nervous, or a similar consistent sequence) specifically so nothing gets skipped under time pressure with a farm waiting for an answer — consistency is a real safeguard against missed findings, not just tidiness.</p>
<h2>Sample selection during necropsy</h2>
<p>Deciding what to collect (tissues for histopathology, swabs for culture, whole samples for PCR) happens in real time based on gross findings — this module connects directly into Module 2's diagnostic sampling and submission content.</p>
<h2>Necropsying multiple birds, not just one</h2>
<p>A single bird's findings can mislead — necropsying several birds representing different points in the disease course (recently dead vs. clinically affected but still alive vs. apparently unaffected) gives a far more complete flock-level picture than one bird examined in isolation.</p>"""),
    ("Diagnostic Sampling and Laboratory Submission",
     """<h2>Matching the sample to the question</h2>
<p>Histopathology answers "what changed in the tissue," culture answers "what organism is present and viable," PCR answers "is this specific pathogen's genetic material present," and serology answers "has this flock been exposed/responded immunologically" — choosing correctly, often several in combination, gets you a real answer faster and cheaper than guessing.</p>
<h2>Sample handling — where good diagnostics actually get lost</h2>
<p>Correct fixation (formalin ratio and timing for histopathology), correct temperature during transport (chilled, not frozen, for most live-culture submissions unless specifically indicated otherwise), and correct, clearly labeled sample identification are where an otherwise well-planned diagnostic workup most often fails in real practice — not in the lab, but before the sample ever gets there.</p>
<h2>Building a relationship with your diagnostic lab</h2>
<p>A lab that knows your practice and gets adequate case history submitted alongside the sample gives you meaningfully better interpretation than one working from a swab and no context — investing in that relationship (and in submitting real history every time, not just a form) pays off in diagnostic quality.</p>
<h2>Interpreting results in flock context</h2>
<p>A single positive PCR result needs interpretation against clinical signs and flock history — subclinical carriage of some organisms is common and doesn't automatically mean that organism is the cause of the problem you're actually investigating.</p>
<h2>When to escalate to specialist or regulatory involvement</h2>
<p>Suspected reportable disease (Module 3 of the health/biosecurity course in this series covers several) triggers specific notification obligations in most jurisdictions — knowing your local reporting requirements before you need them, not looking them up mid-crisis, is part of practicing responsibly here.</p>"""),
    ("Flock-Level Epidemiology and Outbreak Investigation",
     """<h2>Thinking in populations, not individuals</h2>
<p>An outbreak investigation asks different questions than individual-patient medicine: what's the attack rate, how is it spreading (house to house, farm to farm), what's the likely source, and what intervention actually breaks the transmission chain — population-level thinking, building directly on Module 1's flock-surveillance foundation.</p>
<h2>Constructing an epidemic curve</h2>
<p>Plotting case onset over time reveals real information about source type (a sharp single-peak curve suggests a point-source exposure; a sustained, spreading curve suggests ongoing transmission) — a genuinely useful, learnable diagnostic tool that most clinical training doesn't cover.</p>
<h2>Tracing the likely source</h2>
<p>New introductions, shared equipment or personnel between units, feed or water source changes, and wild bird/vector exposure are the classic categories to investigate systematically — treating this as a structured investigation rather than a guess meaningfully improves your hit rate.</p>
<h2>Case definition and active surveillance</h2>
<p>A clear, consistent case definition (what specifically counts as "affected") lets you accurately track whether an intervention is actually working, rather than relying on impression alone — this discipline is what separates a real outbreak investigation from informal troubleshooting.</p>
<h2>Communicating findings and recommendations</h2>
<p>An outbreak investigation is only useful if its findings translate into a clear, actionable recommendation the farm can actually implement — the same "connect to what the farm manager is optimizing for" principle from Module 5 of the production-economics course applies directly here.</p>"""),
    ("Antimicrobial Stewardship in Poultry Production",
     """<h2>Why stewardship is now central to poultry practice</h2>
<p>Antimicrobial resistance is a genuine, escalating concern in poultry production specifically, given historical scale of use — increasing regulatory restriction and buyer/market requirements make stewardship a practical necessity for practice viability, not just an ethical consideration.</p>
<h2>The stewardship hierarchy</h2>
<p>Prevention first (biosecurity, vaccination, nutrition, environment — everything covered earlier in this series) reduces the disease burden that would otherwise require antimicrobial treatment at all; targeted treatment based on actual diagnosis and, where feasible, susceptibility testing comes next; broad, prophylactic, or growth-promotion use is increasingly restricted and, where still permitted, worth scrutinizing even where legal.</p>
<h2>Culture and susceptibility testing in practice</h2>
<p>Building susceptibility testing into your workflow — not just treating empirically every time — improves both individual-case outcomes and contributes real data toward resistance-pattern awareness across your practice's client base.</p>
<h2>Withdrawal periods and residue avoidance</h2>
<p>Any antimicrobial use in food-producing birds carries a withdrawal-period obligation before the birds or their products enter the food supply — miscalculated or ignored withdrawal periods are a genuine food-safety and regulatory-compliance failure, worth treating with real rigor, not an afterthought.</p>
<h2>Documenting and communicating stewardship</h2>
<p>Many buyers and certification schemes now require documented antimicrobial-use records and stewardship plans — a practice that helps farms build genuine, defensible documentation is providing real, differentiated value, connecting back to the practice-building theme of this course's final module.</p>"""),
    ("Building a Poultry-Focused Veterinary Practice",
     """<h2>Why poultry practice rewards genuine specialization</h2>
<p>Poultry medicine has real, learnable depth (as this whole series demonstrates) that most general practices never build — a practitioner who does creates genuine differentiation and becomes the natural go-to for a farm's full range of needs, not just emergency treatment.</p>
<h2>Services beyond reactive treatment</h2>
<p>Flock health consulting, biosecurity program design and auditing (Module 2 of the health/biosecurity course), vaccination program design (Module 5 of that same course), welfare auditing (Module 3 of the production course), and necropsy/diagnostic services (Modules 1-2 of this course) are all real, billable services beyond "come treat my sick flock."</p>
<h2>Building farm relationships that last</h2>
<p>Regular scheduled flock visits, not just emergency response, build the kind of ongoing relationship where a practice becomes genuinely embedded in a farm's operation — proactive, scheduled engagement is what separates a trusted poultry practice from an emergency-only vendor.</p>
<h2>Staying current in a fast-moving field</h2>
<p>Disease pressure, vaccine technology, regulatory requirements, and buyer/certification standards all shift over time in poultry production specifically — genuine ongoing continuing education (not a one-time course) is part of what maintaining real expertise here actually requires.</p>
<h2>A closing note on scope</h2>
<p>This series covers real clinical and practice-building depth, but poultry medicine is a genuinely large field — treat this as a strong foundation for building real expertise, not a complete substitute for hands-on mentorship, further specialty training, and accumulated case experience in the field.</p>"""),
]

COURSES = [
    {
        "slug": "poultry-health-and-biosecurity",
        "title": "Poultry Health & Biosecurity for Practitioners",
        "subtitle": "Flock surveillance, biosecurity program design, and the major viral, bacterial, and parasitic diseases — for veterinarians.",
        "level": Course.Level.FOUNDATION,
        "price_ngn": 6000,
        "modules": COURSE_1_MODULES,
        "sales_headline": "The flock-medicine foundation general practice training usually skips",
        "prerequisite_slug": None,
    },
    {
        "slug": "poultry-nutrition-and-production",
        "title": "Poultry Nutrition & Production Systems",
        "subtitle": "Nutrition, housing and welfare, layer vs broiler management, and production economics — for veterinarians.",
        "level": Course.Level.INTERMEDIATE,
        "price_ngn": 6000,
        "modules": COURSE_2_MODULES,
        "sales_headline": "Understand the production math your poultry clients live in every day",
        "prerequisite_slug": "poultry-health-and-biosecurity",
    },
    {
        "slug": "advanced-poultry-practice",
        "title": "Advanced Poultry Practice: Necropsy, Diagnostics & Flock Medicine",
        "subtitle": "Systematic necropsy, diagnostic sampling, outbreak investigation, antimicrobial stewardship, and building a poultry practice.",
        "level": Course.Level.ADVANCED,
        "price_ngn": 8500,
        "modules": COURSE_3_MODULES,
        "sales_headline": "The diagnostic and practice-building skills that make you the poultry vet farms call first",
        "prerequisite_slug": "poultry-nutrition-and-production",
    },
]

FINAL_EXAMS = {
    "poultry-health-and-biosecurity": [
        ("Why is flock-level production and mortality data often a more useful diagnostic signal than one sick bird's exam findings?",
         "A single bird can be a sentinel, but the flock's aggregate mortality curve, feed/water consumption, and production trend often reveal a developing problem earlier and more reliably than one bird's clinical signs alone.",
         "Aggregate flock data often signals a developing problem earlier than one bird's individual findings",
         "Individual bird exam findings are irrelevant to flock-level disease investigation"),
        ("Why does all-in/all-out management reduce disease transmission risk compared to mixed-age housing?",
         "Mixing ages increases transmission risk by continuously introducing susceptible birds alongside potential carriers — all-in/all-out breaks that cycle between flocks.",
         "It avoids continuously mixing susceptible young birds with potential carriers from older groups",
         "Bird age has no real effect on disease transmission dynamics"),
        ("Why can infectious bursal disease (Gumboro) cause problems in a flock well after the acute phase has passed?",
         "It damages the bursa of Fabricius, causing immunosuppression in survivors that leaves the flock more vulnerable to secondary disease for a period afterward.",
         "Surviving birds are often immunosuppressed afterward, raising vulnerability to secondary disease",
         "IBD has no lasting effect on a flock once the acute phase resolves"),
        ("Why is a documented cold-chain failure worse than simply not vaccinating at all, in terms of false confidence?",
         "A program that looks complete on paper but delivered a potency-degraded vaccine creates false confidence that protection exists when it may not.",
         "It can create false confidence that protection exists when the vaccine may have lost potency",
         "Cold-chain failures have no real effect on a vaccine's protective value"),
    ],
    "poultry-nutrition-and-production": [
        ("Why does modern feed formulation target specific amino acids rather than crude protein percentage alone?",
         "Two diets with identical crude protein can perform very differently depending on amino acid balance (especially methionine and lysine) — crude protein alone doesn't capture that.",
         "Amino acid balance, not just total crude protein, determines how two diets actually perform",
         "Crude protein percentage alone fully determines diet performance regardless of amino acid balance"),
        ("Why should water always be considered before assuming a nutritional cause for an unexplained production drop?",
         "Water quality, availability, or palatability issues commonly show up as production problems that get misattributed to feed — ruling water out first avoids chasing the wrong root cause.",
         "Water-related issues are a common, often-overlooked cause of production problems that mimic nutritional ones",
         "Water intake has no meaningful effect on flock production performance"),
        ("Why might a sudden flock-wide feed conversion change with a recent feed delivery, but no clinical disease signs, point toward feed rather than disease?",
         "That pattern — flock-wide, correlated with a feed change, and without disease signs — is a useful heuristic pointing at feed/ingredient issues (like mycotoxin contamination) rather than an infectious cause.",
         "That specific pattern (flock-wide, tied to a feed change, no disease signs) is a useful pointer toward a feed-related cause",
         "Feed changes are never a plausible explanation for a flock-wide performance shift"),
        ("Why is wet, caked litter a health concern beyond just being unpleasant to manage?",
         "It drives ammonia production (harming respiratory health), footpad dermatitis, and creates conditions favorable to pathogen persistence — a genuine preventive-medicine issue, not just housekeeping.",
         "It contributes to ammonia buildup, footpad dermatitis, and pathogen persistence — real health effects",
         "Litter condition is purely a housekeeping matter with no real health implications"),
    ],
    "advanced-poultry-practice": [
        ("Why do most poultry practitioners necropsy several birds from an affected flock rather than just one?",
         "A single bird can mislead; birds representing different points in the disease course together give a far more complete flock-level picture than one bird in isolation.",
         "Multiple birds at different disease stages give a much more complete flock-level picture than one",
         "Necropsying more than one bird provides no additional diagnostic information"),
        ("Why does correct sample handling (fixation, temperature, labeling) matter as much as choosing the right diagnostic test?",
         "An otherwise well-chosen diagnostic test can fail simply from poor handling before the sample ever reaches the lab — this is where real workups most often break down in practice.",
         "Poor sample handling before submission is a common, real point of diagnostic failure",
         "Sample handling has no real bearing on diagnostic outcomes as long as the right test was ordered"),
        ("What does a sharp, single-peak epidemic curve typically suggest compared to a sustained, spreading curve?",
         "A sharp single peak suggests a point-source exposure, while a sustained spreading curve suggests ongoing transmission — genuinely different investigative implications.",
         "A single sharp peak suggests a point-source exposure rather than ongoing spreading transmission",
         "The shape of an epidemic curve carries no real diagnostic information"),
        ("Why does the antimicrobial stewardship hierarchy put prevention (biosecurity, vaccination, nutrition) ahead of treatment?",
         "Reducing the underlying disease burden through prevention lowers how often antimicrobial treatment is needed at all — treatment is positioned after prevention, not as the first response.",
         "Reducing disease burden through prevention lowers how often antimicrobial treatment becomes necessary",
         "Prevention and treatment are equally weighted with no meaningful ordering between them"),
    ],
}


class Command(BaseCommand):
    help = (
        "Seeds a 3-course poultry series for veterinarians (health & biosecurity, "
        "nutrition & production, advanced/necropsy-diagnostics) with real written "
        "content, prerequisite gating between tiers, and final exams. Safe to re-run."
    )

    def handle(self, *args, **options):
        org = Organization.objects.filter(slug="xpress-digital-academy").first()
        if not org:
            self.stderr.write(self.style.ERROR("Run seed_demo_course first — no Organization found."))
            return

        programme, _ = Programme.objects.get_or_create(
            organization=org, slug="veterinary-continuing-education",
            defaults={
                "title": "Veterinary Continuing Education",
                "audience": Audience.VET,
                "description": "Clinical continuing-education courses for licensed veterinarians and vet techs.",
            },
        )

        created_courses = {}
        with transaction.atomic():
            for spec in COURSES:
                prerequisite = created_courses.get(spec["prerequisite_slug"]) if spec["prerequisite_slug"] else None
                if spec["prerequisite_slug"] and not prerequisite:
                    prerequisite = Course.objects.filter(slug=spec["prerequisite_slug"]).first()

                course, created = Course.objects.get_or_create(
                    organization=org, programme=programme, slug=spec["slug"],
                    defaults={
                        "title": spec["title"],
                        "subtitle": spec["subtitle"],
                        "description": f"<p>{spec['sales_headline']}</p>",
                        "audience": Audience.VET,
                        "level": spec["level"],
                        "pricing_model": Course.PricingModel.PAID,
                        "price_ngn": spec["price_ngn"],
                        "access_type": Course.AccessType.LIFETIME,
                        "requires_final_assessment": True,
                        "estimated_hours": 3.5,
                        "is_published": False,
                        "prerequisite": prerequisite,
                        "sales_headline": spec["sales_headline"],
                        "instructor_bio": "Dr. Omale Ojonimi Samuel, veterinarian (VCN 9217).",
                    },
                )
                created_courses[spec["slug"]] = course

                if not created:
                    self.stdout.write(self.style.WARNING(f"{course.title} already exists — leaving as-is."))
                    continue

                self.stdout.write(self.style.SUCCESS(f"Created course: {course}"))
                for i, (title, body) in enumerate(spec["modules"], start=1):
                    module = Module.objects.create(
                        course=course, order=i, title=title, unlock_rule=Module.UnlockRule.SEQUENTIAL,
                    )
                    Lesson.objects.create(
                        module=module, order=1, title=f"Module {i}: {title}", type=Lesson.Type.TEXT,
                        body=body.strip(), is_preview=(i == 1),
                    )
                self.stdout.write(self.style.SUCCESS(f"  {len(spec['modules'])} modules created."))

                if Quiz.objects.filter(scope=Quiz.Scope.FINAL, course=course).exists():
                    continue
                questions = FINAL_EXAMS[spec["slug"]]
                bank = QuestionBank.objects.create(
                    organization=org, name=f"{course.title} — Final Exam",
                    description=f"Covers all modules of {course.title} — must be passed to unlock the certificate.",
                )
                for stem, explanation, correct, wrong in questions:
                    q = Question.objects.create(
                        bank=bank, type=Question.Type.MCQ, stem=stem, explanation=explanation,
                        difficulty=Question.Difficulty.HARD,
                    )
                    Choice.objects.create(question=q, text=correct, is_correct=True, order=1)
                    Choice.objects.create(question=q, text=wrong, is_correct=False, order=2)
                Quiz.objects.create(
                    scope=Quiz.Scope.FINAL, course=course, title=f"Final Exam — {course.title}",
                    instructions=f"{len(questions)} questions covering the full course. Pass to unlock your certificate.",
                    bank=bank, question_count=len(questions), pass_mark=70,
                    max_attempts=0, time_limit_minutes=0,
                )
                self.stdout.write(self.style.SUCCESS("  Created final exam."))

        self.stdout.write(self.style.SUCCESS(
            "Done. All courses unpublished — review, set Vertical + Approved + is_published in admin for each."
        ))
