from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.catalog.models import Course, Lesson

# Real, written lesson content for the "Practical Dog Breeding for
# Nigerian Breeders" demo course — replaces the placeholder VIDEO
# lessons the seed command creates with genuine TEXT content, so the
# course is actually usable (and free) to send to real breeders
# without waiting on video production. Keyed by module order (1-8),
# matching apps.catalog.management.commands.seed_demo_course.MODULES.
#
# Deliberately general-knowledge animal husbandry guidance, not
# clinical instruction — every module that touches health routes the
# actual decision back to "call your vet," consistent with the
# course's own stated philosophy (see Course.not_for on this course).
# No specific drug names or dosages are given anywhere here.

LESSON_CONTENT = {
    1: """
<h2>Why you're breeding matters more than you think</h2>
<p>Before anything else — before the stud, before the timing, before the whelping box — decide honestly why you're breeding this litter. "Because she's a good dog" is not a plan. A real reason sounds like: improving temperament in the line, correcting a structural fault you keep seeing, or producing puppies suited to a specific kind of work or home. That reason should guide every choice you make from here.</p>

<h2>Selecting the dam and sire</h2>
<p>Look past coat colour and cuteness. What you actually want to evaluate:</p>
<ul>
<li><strong>Temperament</strong> — is this a dog you'd want ten more of? Fear and aggression are strongly heritable.</li>
<li><strong>Conformation</strong> — structure that matches the breed standard isn't vanity, it's function: a dog built correctly moves, breathes, and ages better.</li>
<li><strong>Health history</strong> — the dog's own health, and what you know of its parents and littermates.</li>
</ul>

<h2>Health screening before mating</h2>
<p>This is not optional if you're breeding seriously. At minimum, both dam and sire should be assessed by a vet as fit for breeding, current on relevant vaccinations, and free of obvious hereditary conditions common to the breed. Ask your vet what screening makes sense for your specific breed — this varies a lot between, say, a Rottweiler and a Lhasa Apso.</p>

<h2>Inbreeding vs line-breeding, in plain language</h2>
<p><strong>Line-breeding</strong> means mating relatives that share a common, usually distant, ancestor — done deliberately to concentrate traits you want. <strong>Inbreeding</strong> is the same idea taken too close (siblings, parent-to-offspring) and concentrates <em>everything</em> — the good and the hidden bad — much faster than most new breeders realise. If you're not experienced enough to read a pedigree and understand coefficient of inbreeding, the safe default is: don't breed close relatives.</p>

<h2>Why records matter</h2>
<p>Start a kennel record system before your first litter, not after your fifth. At minimum, track: matings and dates, whelping dates and litter outcomes, any health issues in parents or puppies, and who each puppy went to. This isn't bureaucracy — it's the data that tells you, two years from now, whether a particular pairing is actually worth repeating.</p>
""",
    2: """
<h2>Stages of the heat cycle</h2>
<p>A bitch's cycle has four stages: <strong>proestrus</strong> (swelling, bloody discharge, she attracts males but won't accept mating), <strong>estrus</strong> (discharge lightens, she becomes receptive — this is the fertile window), <strong>diestrus</strong> (she's no longer receptive, whether or not she's pregnant), and <strong>anestrus</strong> (the resting phase between cycles).</p>

<h2>Reading the signs</h2>
<p>Visible signs — swelling, discharge, a male's interest, her own behaviour (flagging her tail to the side) — tell you a cycle is happening, but they don't reliably tell you the exact fertile day. This is the single most common mistake new breeders make.</p>

<h2>Why most missed matings are timing failures</h2>
<p>Standing heat (accepting a mate) can start before ovulation actually happens. Breeders who mate purely "on the first sign" often miss the real window entirely — and a bitch that fails to conceive from bad timing sometimes gets wrongly labelled infertile, when timing was the actual problem.</p>

<h2>What testing tells you</h2>
<p>Two tools your vet can use to pin down timing precisely: <strong>vaginal cytology</strong> (a swab read under a microscope, showing how the cells are changing through the cycle) and <strong>progesterone testing</strong> (a blood test that tracks the hormone surge that triggers ovulation). Neither is required for every mating, but if a pairing is expensive, difficult to arrange, or has failed before, they're worth the cost.</p>

<h2>Counting from the right day</h2>
<p>Whelping-date calculators (like the 63-day rule covered in Module 4) are only as accurate as the day you start counting from. "Day 1 of proestrus" and "day of ovulation" are not the same day, and confusing them throws off your whole calendar. When in doubt, confirm with your vet rather than guess.</p>
""",
    3: """
<h2>Natural mating and the tie</h2>
<p>In a natural mating, dogs typically "tie" — a period where they're physically locked together, usually 10-30 minutes, sometimes longer. This is normal dog reproductive biology, not a sign anything has gone wrong. Don't try to force a separation.</p>

<h2>What to do when it fails</h2>
<p>A mating can fail for many reasons: bad timing (see Module 2), an inexperienced or reluctant pair, a size mismatch, or an underlying health issue in either dog. If repeated attempts fail, that's a reason to involve your vet rather than keep trying blind — there may be a fixable cause, or it may be a sign this pairing isn't going to work.</p>

<h2>An honest introduction to artificial insemination (AI)</h2>
<p>AI exists for real, legitimate reasons: the dogs are in different locations, a size or temperament mismatch makes natural mating unsafe, or you're using stored semen from a stud that's no longer available. It requires proper technique and, for the best success rates, the same timing precision discussed in Module 2. This is a service to arrange through your vet or a specialist, not something to improvise.</p>

<h2>Evaluating a stud before you pay for him</h2>
<p>Ask for the same things you'd want shown about your own dog: health clearances, temperament, structure, and — if he's proven — the health and temperament of his previous litters. A stud's popularity is not the same as a stud's suitability for your specific bitch.</p>

<h2>The popular-sire problem</h2>
<p>When one dog is used heavily across a breed population because he's a big winner or highly promoted, his genes — including any hidden faults — spread disproportionately through the whole gene pool. This is a real, documented issue in purebred dog breeding. It's worth asking not just "is this stud good?" but "how many litters has he already sired?"</p>

<h2>Stud service agreements</h2>
<p>Put the arrangement in writing before mating, not after: the fee (and whether it's per-mating or per-live-puppy), what happens if the bitch doesn't conceive, pick-of-litter arrangements if any, and who's responsible for travel/care if the dogs need to be together for a period. A short written agreement prevents most disputes.</p>
""",
    4: """
<h2>Confirming pregnancy — and when</h2>
<p>Pregnancy can usually be confirmed by a vet via palpation from around day 21-28, or more reliably by ultrasound from around day 25-30. Blood tests for relaxin (a pregnancy-specific hormone) are also available from around day 25-30. Guessing based on behaviour alone is unreliable — confirm properly if you need to know for certain (for buyer deposits, for example).</p>

<h2>Feeding through each stage</h2>
<p>For roughly the first two-thirds of pregnancy, most bitches don't need a dramatic diet change beyond good-quality food. In the final third, nutritional needs rise significantly as puppies grow fast — this is when a gradual shift to a higher-calorie, nutrient-dense diet (many breeders use a good-quality puppy food during this stage) usually starts. Talk to your vet about the right feeding plan for your specific bitch and breed size.</p>

<h2>Medicines and dewormers — what's safe</h2>
<p>Not everything safe for a non-pregnant dog is safe during pregnancy. Never give any medication, dewormer, or supplement to a pregnant bitch without checking with your vet first — including things that seem routine. This is one of the clearest lines in this whole course between "your judgement" and "call the vet": medication decisions during pregnancy are not a DIY area.</p>

<h2>Exercise</h2>
<p>Moderate, regular exercise is good through most of pregnancy — it supports fitness for labour. In the final one to two weeks, ease off to gentler activity as she becomes less comfortable and more focused on nesting.</p>

<h2>Preparing the whelping box</h2>
<p>Set it up at least a week before the due date so she has time to settle into it. It should be warm, draft-free, easy for her to enter and leave but with sides high enough to contain wobbly newborn puppies, and lined with washable, changeable bedding. Place it somewhere quiet, away from household traffic.</p>

<h2>The 63-day calendar</h2>
<p>Average gestation in dogs is about 63 days from ovulation (not from the mating date, which can differ by a few days — see Module 2 on timing). Use this as a planning guide, not a guarantee — normal whelping can happen anywhere from about day 58 to day 68 from ovulation. If she goes well past that window, contact your vet.</p>
""",
    5: """
<h2>Signs labour is starting</h2>
<p>Common early signs: restlessness, nesting behaviour, a drop in body temperature (often below the normal range in the 12-24 hours before labour), loss of appetite, and panting. Not every bitch shows every sign clearly — familiarity with your own dog's normal behaviour helps you notice the change.</p>

<h2>Normal progression, stage by stage</h2>
<p>Labour has three broad stages: <strong>Stage 1</strong> — early contractions (not always visible from outside), restlessness, possible shivering, can last several hours. <strong>Stage 2</strong> — active straining and delivery of puppies, usually with a placenta following each puppy (though not always immediately). <strong>Stage 3</strong> — delivery of remaining placentas; in a multi-puppy litter, stages 2 and 3 often repeat/overlap as she delivers puppies one after another.</p>

<h2>What you can safely do</h2>
<p>Stay present but avoid unnecessary interference. Keep the space calm and quiet. Let her clean each puppy and chew the cord herself where possible — this is normal and stimulates the puppy to breathe. Have clean towels ready in case a puppy needs help clearing its airway or stimulation to breathe.</p>

<h2>The red flags that mean call the vet NOW</h2>
<ul>
<li>Strong, visible straining for more than 30-60 minutes with no puppy delivered</li>
<li>More than 2-4 hours between puppies with no sign of active labour</li>
<li>Green or dark discharge <em>before</em> the first puppy arrives</li>
<li>Visible distress, extreme lethargy, or collapse</li>
<li>You know or suspect more puppies remain but labour appears to have stopped</li>
</ul>
<p>When in doubt, call. A phone call that turns out to be unnecessary costs you a few minutes. A delay on a real emergency can cost the litter, or the dam.</p>

<h2>Understanding dystocia and caesareans</h2>
<p><strong>Dystocia</strong> is difficult or obstructed labour — it can be caused by an oversized puppy, poor positioning, a narrow pelvis, or a weak/exhausted uterus, among other things. A caesarean isn't a failure on your part — for some breeds (notably brachycephalic/flat-faced breeds) and some individual dogs, it's the safe, expected outcome, and knowing that in advance is part of responsible planning, not something to feel bad about.</p>

<h2>Assembling a whelping kit</h2>
<p>Clean towels, a digital thermometer, a bulb syringe (for clearing airways), clean scissors and thread (for cord-tying if needed), a heat source for chilled puppies, a scale for daily weighing, and your vet's phone number — including their after-hours/emergency contact — written down somewhere you won't have to search for it in a panic.</p>
""",
    6: """
<h2>Colostrum and the first 12 hours</h2>
<p>Colostrum — the first milk — carries antibodies a newborn puppy cannot get any other way. A puppy's gut can only absorb these antibodies efficiently in roughly the first 12-24 hours of life, after which that "window" closes. Getting every puppy nursing within the first few hours of birth is one of the single most important things you can do for the whole litter's health.</p>

<h2>Keeping neonates warm</h2>
<p>Newborn puppies can't regulate their own body temperature for the first couple of weeks. A chilled puppy stops digesting food properly, gets weaker, and can spiral quickly. The whelping area should stay warm (many breeders aim for a nest temperature in the high-20s°C for the first week, gradually easing as puppies grow) — but always leave the dam room to move away from heat if she's too warm herself.</p>

<h2>Weighing daily</h2>
<p>Weigh every puppy at the same time each day and keep a written log. A puppy should gain weight steadily. A puppy that loses weight or fails to gain for more than a day is telling you something is wrong before it becomes visibly obvious — this is the single best early-warning tool a breeder has.</p>

<h2>Recognising a fading puppy</h2>
<p>Watch for: reluctance to nurse, constant crying (a content, fed puppy is usually quiet), separating from the litter pile, a cold feel to the touch, or limpness. Any of these in the first days of life is urgent — don't wait to see if it resolves on its own.</p>

<h2>Hypothermia and hypoglycaemia</h2>
<p>These two problems feed each other: a cold puppy can't digest food, so it doesn't get energy, so its temperature drops further. The correct order matters — warm a chilled puppy <em>gradually</em> before attempting to feed it; feeding a still-cold puppy can make things worse, not better.</p>

<h2>Supplemental and tube feeding</h2>
<p>If a puppy isn't nursing adequately (being pushed out by stronger littermates, a dam with insufficient milk, or a puppy too weak to latch), supplemental feeding may be needed. Tube feeding especially requires being shown the correct technique by your vet — done wrong, it risks the puppy inhaling milk into its lungs. Don't attempt it for the first time without guidance.</p>

<h2>When to intervene, when to let nature work</h2>
<p>Healthy litters mostly manage themselves — dams are generally excellent at this. Your job is mostly close observation: daily weights, watching behaviour, keeping the environment right — and knowing the specific red flags above that mean it's time to step in or call your vet.</p>

<h2>Early socialisation</h2>
<p>From around 3 weeks, as puppies' eyes and ears open and they become mobile, gentle, varied, positive handling and exposure to everyday sounds and surfaces starts shaping how confident and adaptable they'll be as adults. This doesn't need to be elaborate — just regular, calm, positive contact.</p>
""",
    7: """
<h2>Parvovirus and distemper — how they actually behave here</h2>
<p>Both are serious, often fatal, highly contagious viral diseases, and both remain genuinely common in many Nigerian kennel environments — not a distant risk. Parvovirus in particular can survive in the environment for a long time and spreads easily via contaminated ground, shoes, and equipment. Puppies are especially vulnerable in the gap after their maternal antibody protection fades but before their own vaccination series is complete.</p>

<h2>Vaccination schedules and the cold chain</h2>
<p>Vaccines only work if they've been stored correctly at every step — this is the "cold chain," and it's a real, practical problem where power supply is unreliable. A vaccine that's been left warm too long during transport or storage may simply not work, even if it was administered correctly. Buy vaccines only from a source you trust to have handled this properly, and follow your vet's recommended schedule rather than a generic one you found online.</p>

<h2>Counterfeit product red flags</h2>
<p>Unfortunately real in some markets: prices that seem too low, packaging that looks slightly "off" (blurry printing, wrong fonts, missing batch numbers), a seller who can't tell you proper storage history, or vaccines bought outside a proper vet/pharmacy supply chain. When in doubt, buy through your vet directly.</p>

<h2>Quarantine for new arrivals</h2>
<p>Any new dog entering your kennel — purchased, rescued, or returning from a show or stud visit — should be kept separate from your existing dogs, especially puppies, for a period (commonly 2 weeks, though ask your vet for guidance specific to the situation) before mixing. This single habit prevents a huge share of kennel disease outbreaks.</p>

<h2>Ticks and tick-borne disease</h2>
<p>Ticks are a genuine, everyday problem in many Nigerian environments and carry diseases that can seriously harm adult dogs and puppies alike. Regular tick prevention (as recommended by your vet for your specific situation) and physical checks after your dogs have been outside are both worth the habit.</p>

<h2>Brucella canis</h2>
<p>A less commonly discussed but serious concern for breeders specifically: Brucella canis is a bacterial infection that can cause infertility, pregnancy loss, and stillbirths, and it's transmissible between dogs (including at mating) and, rarely, to humans. Breeding dogs — especially studs used with multiple bitches, or bitches from an unfamiliar source — are worth discussing Brucella screening for with your vet, particularly if you're breeding commercially.</p>

<h2>Kennel hygiene on a real budget</h2>
<p>You don't need expensive equipment for this to work: regular cleaning of sleeping and feeding areas, separate feeding bowls per dog where possible, prompt removal of waste, and hand-washing between handling different dogs (especially between a sick dog and healthy ones) go a very long way on their own.</p>
""",
    8: """
<h2>Costing a litter honestly</h2>
<p>Before you price puppies, know your real costs: stud fee (or AI costs), pre-breeding health checks for both parents, pregnancy and whelping vet care, extra feed for the pregnant/nursing dam, puppy vaccinations and deworming, and a buffer for anything that goes wrong (a caesarean, a fading puppy needing intensive care). Breeders who skip this step often discover, after the fact, that they barely broke even — or lost money — on a litter they assumed was profitable.</p>

<h2>Pricing puppies</h2>
<p>Price against your real costs and the breed/quality level, not just "what others are charging" copied from an online listing. Consider whether you're pricing pet-quality and breeding/show-quality puppies from the same litter differently, which is common and reasonable practice.</p>

<h2>Screening buyers</h2>
<p>A good buyer conversation covers: why they want this specific breed, their living situation and experience with dogs, and what happens to the puppy if their circumstances change. This isn't about being difficult — it's the single biggest thing you can do to reduce the number of your puppies that end up abandoned or in poor homes later.</p>

<h2>Deposits and contracts</h2>
<p>A simple written agreement protects both sides: deposit amount and whether it's refundable, what health guarantees you're offering (and for how long), and what happens if a health issue traceable to breeding shows up after sale. You don't need a lawyer to write something clear and fair — you do need it in writing.</p>

<h2>Safe transport</h2>
<p>However the puppy travels to its new home, prioritise a secure carrier, appropriate temperature, and minimal stress. A puppy's first experience of travel shapes how it feels about travel for a long time afterward.</p>

<h2>Handling a buyer whose puppy falls sick</h2>
<p>Respond promptly and take it seriously, even when it's inconvenient. How you handle a problem after the sale is what your reputation is actually built on — good or bad word of mouth in the breeder community travels fast.</p>

<h2>Building a kennel reputation</h2>
<p>Reputation is built slowly, from many small things done consistently right: honest answers to buyer questions, transparent health history, following through on guarantees, and being someone other breeders would vouch for.</p>

<h2>Welfare, and knowing when not to breed</h2>
<p>Sometimes the right call is not breeding a particular pairing, not breeding this cycle, or not breeding this dog at all — because of age, health, temperament, or simply because you can't currently give a litter the care it needs. A breeder willing to say "not this time" is exactly the kind of breeder this course is trying to help you become.</p>
""",
}


class Command(BaseCommand):
    help = (
        "Replaces the placeholder VIDEO lessons on the Practical Dog Breeding "
        "demo course with real, written TEXT content (no video required). "
        "Safe to re-run — always overwrites with the content above."
    )

    def handle(self, *args, **options):
        try:
            course = Course.objects.get(slug="practical-dog-breeding")
        except Course.DoesNotExist:
            raise CommandError(
                "Course 'practical-dog-breeding' not found — run "
                "`seed_demo_course` first."
            )

        updated = 0
        with transaction.atomic():
            for module in course.modules.order_by("order"):
                content = LESSON_CONTENT.get(module.order)
                if not content:
                    self.stdout.write(self.style.WARNING(
                        f"No written content for module {module.order} ({module.title}) — skipped."
                    ))
                    continue
                lesson = module.lessons.order_by("order").first()
                if not lesson:
                    continue
                lesson.type = Lesson.Type.TEXT
                lesson.body = content.strip()
                lesson.video_id = ""
                lesson.video_provider = ""
                lesson.save(update_fields=["type", "body", "video_id", "video_provider"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Updated {updated} lessons with real written content."))
