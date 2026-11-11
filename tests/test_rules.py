"""Rule tests. All texts below are SYNTHETIC examples written for testing -
they are not real people and never appear in the results.

Run:  python -m pytest tests -q      (or: python tests/test_rules.py)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from prospector import qualify, textsig  # noqa: E402


def sig(text, platform="reddit", context="r/indianrealestate", title="", city="", state="", lang="",
        date="2026-09-01", author="tester", prop=False, owner=False):
    clean, had = textsig.clean_text(text)
    return {"platform": platform, "kind": "post", "id": "x", "post_id": "x", "author_id": author,
            "author_name": author, "text": clean, "had_contact": had, "url": "https://example.invalid/x",
            "date": date, "context": context, "context_title": title, "context_city": city,
            "context_state": state, "context_lang": lang, "context_is_property": prop, "is_owner": owner}


def run(*sigs, today="2026-11-11"):
    for s in sigs:
        qualify.assess(s)
    p = qualify.build_prospect(list(sigs))
    p["status"], p["reason"], p["unverified"] = qualify.classify(p, today)
    return p


def test_redaction_removes_contact_details():
    out, had = textsig.clean_text("Interested, call me +91 98765 43210 or a.b@mail.com. Budget 1,50,00,000")
    assert had and "98765" not in out and "@" not in out and "1,50,00,000" in out


def test_strong_needs_intent_specifics_and_location():
    p = run(sig("I'm from Chennai and planning to buy a 1BHK in Dubai, JVC. Budget around 1.2 cr, off-plan or ready?"))
    assert p["status"] == "strong_signal"
    assert (p["loc"]["city"], p["loc"]["state"], p["loc"]["tier"]) == ("Chennai", "Tamil Nadu", "explicit")


def test_intent_without_specifics_is_not_strong():
    p = run(sig("I live in Hyderabad. How can I buy property in Dubai?"))
    assert p["status"] == "needs_validation"


def test_job_title_or_location_alone_is_not_intent():
    p = run(sig("Senior director based in Bangalore here. Dubai real estate market is interesting to watch."))
    assert p["status"] == "reject"


def test_broker_is_rejected():
    p = run(sig("We offer the best Dubai apartments for investors from Kochi. DM me for details and payment plan."))
    assert p["status"] == "reject" and "Agent" in p["reason"]


def test_looking_for_a_broker_is_not_a_broker():
    assert "NEG_agent" not in textsig.markers("I am looking for a broker to help me buy in Dubai Marina")


def test_gulf_resident_without_south_base_is_rejected():
    p = run(sig("I am working in Dubai and want to buy a studio in JVC under 600k AED", context="r/dubai"))
    assert p["status"] == "reject"


def test_south_indian_origin_living_abroad_needs_validation():
    p = run(sig("I am from Kerala, working in Dubai. Looking to buy a studio in JVC under 600k AED next year"))
    assert p["status"] == "needs_validation" and "Dubai" in p["reason"]


def test_buying_in_india_is_not_a_dubai_buyer():
    p = run(sig("NRI here. I want to buy a flat in Bangalore, budget 1.5 cr. My cousin has property abroad in the UAE, Dubai real estate is not for me.",
                context="r/bangalore", city="Bengaluru", state="Karnataka"))
    assert p["status"] == "reject"


def test_community_membership_counts_as_location_evidence():
    p = run(sig("Thinking of investing in Dubai property instead of a second flat here. Budget 1 cr, 2BHK off-plan. Anyone done this?",
                context="r/bangalore", city="Bengaluru", state="Karnataka"))
    assert p["status"] == "strong_signal" and p["loc"]["tier"] == "community"
    assert any("inferred" in u for u in p["unverified"])


def test_language_only_location_never_strong():
    p = run(sig("I want to buy 2 bhk, budget 80 lakhs, payment plan details please", platform="youtube",
                context="YouTube: x", title="Dubai property investment Tamil", lang="ta", prop=True))
    assert p["status"] == "needs_validation" and p["loc"]["tier"] == "language"


def test_bare_price_question_on_regional_video_is_rejected():
    p = run(sig("price?", platform="youtube", context="YouTube: x", title="Dubai property Tamil", lang="ta", prop=True))
    assert p["status"] == "reject"


def test_channel_owner_is_rejected():
    p = run(sig("Thanks! I want to buy more units in JVC, budget 1 cr", platform="youtube", context="YouTube: x",
                title="Dubai property Tamil", lang="ta", prop=True, owner=True))
    assert p["status"] == "reject"


def test_stale_signal_is_downgraded():
    p = run(sig("I'm from Chennai and planning to buy a 1BHK in Dubai JVC, budget 1.2 cr", date="2024-02-01"))
    assert p["status"] == "needs_validation" and "months old" in p["reason"]


def test_same_author_is_one_prospect():
    a = sig("I'm in Kochi. Want to buy a studio in Dubai, budget 60 lakhs", author="same")
    b = sig("I'm in Kochi. Want to buy a studio in Dubai, budget 60 lakhs", author="same")
    c = sig("Dubai apartment service charges - what are they?", author="same")
    for s in (a, b, c):
        qualify.assess(s)
    groups, dupes = qualify.group_by_author([a, b, c])
    assert len(groups) == 1 and dupes == 1


# ---- regressions from the code review -------------------------------------------------
def test_third_person_from_is_not_the_authors_residence():
    for text in ("Many investors from Bangalore are buying there", "My friend from Hyderabad bought in Dubai Marina",
                 "flights from Chennai are cheap"):
        assert textsig.find_location(text)["tier"] == "mention", text
    for text in ("I'm from Chennai", "Interested, from Coimbatore", "From Kochi. Please share details", "watching from Hyderabad"):
        assert textsig.find_location(text)["tier"] == "explicit", text
    p = run(sig("Many investors from Bangalore are buying there. I want to buy a 2BHK in Dubai JVC, budget 1 cr.", city="", state=""))
    assert p["status"] != "strong_signal" and p["loc"]["tier"] == "mention"


def test_urgency_is_not_a_purchase_timeline():
    assert "timeline" not in textsig.markers("please send details asap")
    assert "timeline" in textsig.markers("planning to buy next year")
    p = run(sig("I'm from Chennai, please send details asap", platform="youtube", context="YouTube: x",
                title="Dubai property Tamil", lang="ta", prop=True))
    assert p["status"] == "needs_validation"


def test_city_is_only_filled_from_the_authors_own_evidence():
    p = run(sig("I am interested please send me the details", platform="youtube", context="YouTube: x",
                title="Dubai property for Chennai buyers", city="Chennai", state="Tamil Nadu", prop=True))
    row = qualify.to_row(p)
    assert (row["city"], row["state"]) == ("unknown", "unknown") and "Chennai" in row["inferred_region"]
    row = qualify.to_row(run(sig("I'm in Kochi. How can I buy property in Dubai?")))
    assert (row["city"], row["state"], row["inferred_region"]) == ("Kochi", "Kerala", "")


def test_split_phone_numbers_are_redacted_but_dates_and_ranges_are_not():
    for raw in ("call 98765 - 43210", "98765 / 43210", "(98765) (43210)", "ph 98765  -  43210", "+91 - 9876543210"):
        out, had = textsig.clean_text(raw)
        assert had and "43210" not in out, raw
    for raw in ("Launch 2026-11-11 10:30 at expo", "Expo on 11/11/2026 10:30", "AED 850000 - 1200000", "Budget 1,50,00,000"):
        assert textsig.clean_text(raw) == (raw, False), raw


def test_a_buyer_who_pastes_a_listing_link_is_not_an_agent():
    p = run(sig("I'm in Kochi, planning to buy a 1BHK in Dubai JVC, budget 80 lakhs. Is this project any good? https://example.com/listing/1"))
    assert p["status"] == "strong_signal" and "example.com" not in p["best"]["text"]


def test_buyer_phrasing_is_not_agent_language():
    for tail in ("Looking for advice.", "Can anyone recommend a real estate agent there?", "Need expert advice on off-plan.",
                 "I am looking for a property consultant."):
        p = run(sig("I'm in Chennai, planning to buy a 2BHK in Dubai JVC, budget 1.5 cr. " + tail))
        assert p["status"] == "strong_signal", tail
    for seller in ("Anyone who would like to invest in Dubai, please DM. For advise and enquiries.",
                   "I'm based in Dubai and an investment advisor here", "Expert help from Zoltan Properties LLC",
                   "We offer the best Dubai apartments"):
        assert "NEG_agent" in textsig.markers(seller), seller


def test_strong_intent_is_not_rejected_on_one_incidental_word():
    for text in ("My salary is 3 lakhs a month. Budget 1.5 cr, any 2BHK in Dubai JVC? Based in Hyderabad.",
                 "Budget 1 cr for a 1BHK in Dubai JVC to rent out, what yield can I expect? I live in Kochi.",
                 "Budget 1 cr, 2BHK in Dubai, which developers should I avoid? I live in Kochi."):
        assert run(sig(text))["status"] != "reject", text
    assert run(sig("Any job vacancy in Dubai real estate? I am from Kochi"))["status"] == "reject"      # still a job-seeker


def test_naming_a_dubai_community_shows_the_target_is_dubai():
    p = run(sig("Investment advice needed. I own a flat in Bangalore. Now looking for a 2BHK off-plan in JVC or Dubai Hills, "
                "budget 1.5 cr. Yields seem better in Dubai.", context="r/bangalore", city="Bengaluru", state="Karnataka"))
    assert p["status"] == "strong_signal"


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print("ok  ", name)
            except AssertionError as e:
                fails += 1
                print("FAIL", name, e)
    sys.exit(1 if fails else 0)


# ---- the rules that decide outcomes, on the phrasing people really use -----------------
def yt(text, title="Dubai property Tamil", lang="ta", author="viewer", channel="Some Realtor", date="2026-09-01", vid="v1", cid=None, **kw):
    s = sig(text, platform="youtube", context="YouTube: " + channel, title=title, lang=lang, prop=True, author=author, date=date, **kw)
    s["post_id"], s["id"] = vid, cid or (author + text[:12])
    return s


@pytest.mark.parametrize("text", ["Contact number please", "Share the details", "More details please, mobile number please",
                                  "I am interested please send me the details", "Dm pls interested", "price?", "Details"])
def test_price_detail_and_contact_requests_are_all_treated_alike(text):
    """Asking for a phone number is not a stronger signal than asking for details: both are weak."""
    assert textsig.intent_tier(textsig.markers(text))[0] == "weak"
    assert run(yt(text))["status"] == "reject"                                   # language-only location
    assert run(yt(text + ". I'm from Coimbatore"))["status"] == "needs_validation"   # but worth a look once they say where they are


@pytest.mark.parametrize("text", ["How much down payment ?", "What is the rental yield", "What Abt resale value",
                                  "1.2 million advance payment in which account. ESCROW or personal.", "emi എത്ര",
                                  "Generally, how much does a 2bhk start from maam?", "Property vangichaal golden visa kittuoo?"])
def test_a_buying_question_outranks_a_contact_request(text):
    assert textsig.intent_tier(textsig.markers(text))[0] == "medium"
    assert run(yt(text))["status"] == "needs_validation"


@pytest.mark.parametrize("text", ["Housing fee is considered as a tax in Dubai.", "He didn't talk about service charges for flats in Dubai.",
                                  "10% rental yield is over estimation. 4-5% for 1 bhk is the market rate.", "Bro sri lankan tax is 200%",
                                  "I can get a nice 4 bhk villa in bangalore in that price"])
def test_a_statement_that_uses_buying_words_is_not_a_question(text):
    assert "buying_question" not in textsig.markers(text)
    assert textsig.intent_tier(textsig.markers(text))[0] in ("", "weak")


@pytest.mark.parametrize("text", ["I want to sell my flat", "I am looking for a tenant for my apartment", "I want to rent a flat",
                                  "suppose he finds another person ready to buy that same property", "my brother wants to buy there",
                                  "I don't want to buy", "if you want to invest you can"])
def test_selling_renting_third_person_and_denials_are_not_purchase_intent(text):
    assert "purchase_intent" not in textsig.markers(text)


@pytest.mark.parametrize("text", ["bro I want to buy a flat", "Hi brother please can help I whand buy home", "How to invest frm india",
                                  "Ippo investment possible ah sir", "Ala invest cheyali??", "oru villa vangan kazhiyumo",
                                  "dubai la veedu vaanganum", "துபாயில் வீடு வாங்க எவ்வளவு ஆகும்?", "ദുബായിൽ ഒരു ഫ്ലാറ്റ് വാങ്ങണം", "దుబాయ్ లో ఇల్లు కొనాలి"])
def test_purchase_intent_in_english_romanised_and_native_script(text):
    assert "purchase_intent" in textsig.markers(text), text


@pytest.mark.parametrize("text", ["ദുബായിൽ പ്രോപ്പർട്ടി വാങ്ങാൻപറ്റില്ല", "இந்த வீடு யாரும் வாங்காதீர்கள்", "சிம்பு வீடு வாங்கி இருக்காரு",
                                  "Saudiyil ippol investment cheyyan pattilla"])
def test_native_and_romanised_denials_or_reports_are_not_intent(text):
    assert "purchase_intent" not in textsig.markers(text), text


@pytest.mark.parametrize("text,city", [("I am living chennai i bought flat", "Chennai"), ("naan Madurai la irukken", "Madurai"),
                                       ("njan Kochi il aanu", "Kochi"), ("nenu Hyderabad nundi", "Hyderabad"),
                                       ("நான் மதுரையில் இருக்கிறேன்", "Madurai"), ("நான் நாகர்கோவிலைச் சேர்ந்தவன்", "Nagercoil"),
                                       ("ഞാൻ ആലപ്പുഴയിൽ ആണ്", "Alappuzha"), ("నేను హైదరాబాద్‌లో ఉంటాను", "Hyderabad")])
def test_residence_stated_in_regional_languages_counts(text, city):
    loc = textsig.find_location(text)
    assert (loc["tier"], loc["city"]) == ("explicit", city), text


@pytest.mark.parametrize("text", ["A Hyderabad based builder is selling units", "Flights, from Chennai to Dubai are cheap",
                                  "Many investors from Bangalore are buying", "My brother is living in Chennai"])
def test_places_that_are_not_the_authors_home(text):
    assert textsig.find_location(text)["tier"] == "mention", text


def test_regional_residence_plus_intent_can_reach_strong_signal():
    p = run(yt("naan Madurai la irukken. I want to buy a 2BHK in JVC, budget 80 lakhs"))
    assert p["status"] == "strong_signal" and p["loc"]["city"] == "Madurai"


def test_someone_who_says_they_are_in_the_gulf_is_not_south_india_based():
    assert run(yt("Ipo abudhabi anu, cheriya oru villa vangan kazhiyumo", lang="ml"))["status"] == "reject"


def test_job_and_rent_rules_only_catch_seekers():
    for text in ("If you lost your job you can use it as rental income", "Min salary for a home loan?", "any vacancy risk for tenants?",
                 "is there an option to rent out the unit?"):
        mk = textsig.markers(text)
        assert not (mk & {"NEG_job", "NEG_rent"}), text
    assert "NEG_job" in textsig.markers("any job vacancy in dubai for freshers")
    assert "NEG_rent" in textsig.markers("I want to rent a room, any bed space available?")
    assert "NEG_agent" not in textsig.markers("We want to register it under our LLC, is that allowed?")


def test_an_existing_owner_is_kept_for_validation():
    p = run(yt("I am living chennai i bought flat there"))
    assert p["status"] == "needs_validation" and "already bought" in p["reason"]


def test_comments_under_the_same_video_are_read_together_but_not_across_videos():
    a = yt("I am interested bro please tell me how to buy property in dubai", author="hb", vid="v1")
    b = yt("I have only 25L", author="hb", vid="v1")
    p = run(a, b)
    assert p["tier"] == "strong" and "budget" in p["markers"] and "25L" in qualify.to_row(p)["evidence_of_interest"]
    c = yt("I am interested bro please tell me how to buy property in dubai", author="hb2", vid="v1")
    d = yt("I have only 25L", author="hb2", vid="v2")
    assert run(c, d)["tier"] == "medium"


def test_a_reply_to_the_creator_is_an_enquiry_but_a_reply_to_a_viewer_is_discussion():
    q = "how many years is the emi? Which bank?"
    assert run(yt("@SomeRealtor " + q, channel="Some Realtor"))["status"] == "needs_validation"
    assert run(yt("@other_viewer12 " + q, channel="Some Realtor"))["status"] == "reject"


def test_shortlist_order_puts_real_location_and_stated_intent_first():
    stated = run(yt("I want to invest, pls guide me, im from Chennai", author="a1"))
    asked = run(yt("What will be the rental income", author="a2", date="2026-10-01"))
    wants = run(yt("How to invest from india", author="a3"))
    order = sorted([asked, wants, stated], key=lambda p: -qualify.rank_key(p, "2026-11-11"))
    assert [p["author_id"] for p in order] == ["a1", "a3", "a2"]


# ---- gaps found by an independent read of every commenter --------------------------------
@pytest.mark.parametrize("text", ["I would like to invest please let me know the details", "How much maintenance fees ? You didn't mention clearly",
                                  "Villakku yearly service charege undoo", "Hand over in which year ?",
                                  "Is it 15 lakhs is advance and remaining we need to pay ?"])
def test_buyer_phrasings_the_rules_used_to_miss(text):
    assert run(yt(text))["status"] == "needs_validation"


@pytest.mark.parametrize("text", ["pls number", "Location??", "How to connect with you", "Still available", "please share ur number",
                                  "Hi, what is the total cost", "price", "Details pls"])
def test_one_line_requests_count_as_a_weak_enquiry(text):
    assert textsig.intent_tier(textsig.markers(text))[0] == "weak"


@pytest.mark.parametrize("text", ["Bangalore property price went up by 100% within 2 years", "This video is totally wrong details.",
                                  "I can get a nice 4 bhk villa in bangalore in that price",
                                  "Lease hold is leasing for 99 years. Any nationalities can buy the property"])
def test_a_price_or_detail_word_in_a_statement_is_not_an_enquiry(text):
    assert "enquiry" not in textsig.markers(text) and "buying_question" not in textsig.markers(text)


@pytest.mark.parametrize("text", ["Get in touch with me, I'll help you out. I'm a Telugu realtor in UAE.",
                                  "I am starting in dubai working as a property consultant",
                                  "Nenu Realestate lo job Chesthunnanu please let me know if you need any assistance"])
def test_sellers_describing_themselves_are_rejected(text):
    assert run(yt(text))["status"] == "reject" and "NEG_agent" in textsig.markers(text)


# ---- findings of two independent reviews -------------------------------------------------
@pytest.mark.parametrize("text", [
    "naan Dubai la oru 2BHK vaanganum, budget 80 lakhs", "nan dubai la veedu vaanganum sir, epdi process?",
    "nenu Dubai lo flat konali anukuntunna, 1 cr budget undi", "naanu Dubai alli mane kollabeku, hege invest madodu?",
    "Dubai il aanu nalla investment, njan oru studio vaanganam ennu vicharikkunnu",
    "Please guide me in Dubai property investment, I want to buy a 1BHK",
    "I want to buy a villa and get settled in Dubai with family next year",
    "I want to buy a 2BHK in JVC and rent it out, what yield can I expect?",
    "I want to book a 1BHK apartment in Dubai, how much is the booking amount?"])
def test_a_buyer_who_names_dubai_as_where_the_property_is_is_not_a_dubai_resident(text):
    p = run(yt(text))
    assert p["status"] == "needs_validation" and not p["abroad"], p["reason"]


@pytest.mark.parametrize("text", ["Ipo abudhabi anu, cheriya oru villa vangan kazhiyumo", "I am working in Sharjah, want to buy a studio",
                                  "naan Dubai la irukken, oru flat vaanganum", "How to connect with you I am from saudhi arabiya"])
def test_someone_who_says_they_are_abroad_is_still_caught(text):
    p = run(yt(text))
    assert p["status"] == "reject" and p["abroad"], p["reason"]


@pytest.mark.parametrize("text", [
    "I'm from Chennai. Need 2bhk for rent in Dubai, budget 50000 aed per year",                 # a renter with a budget
    "I am from Hyderabad. I want to sell my 2bhk in JVC, price around 900k AED any buyers?",     # a seller with a price
    "I'm from Chennai. I want to buy a flat in Chennai next year, Dubai is too costly for me",   # buying in India
    "I'm from Chennai, planning to book tickets to Dubai next month", "I want to buy Burj Khalifa 😂😂", "dubai la gold vaanganum",
    "Is it worth to buy a car in Dubai or better to rent?", "2bhk rent evlo bro?", "Studio monthly rent how much in International City?",
    "Is JVC safe for bachelors to stay?", "Do you have a 1bhk for rent in JVC? monthly payment ok?",
    "Looking to invest in Dubai? Contact us today!", "Want to buy property in Dubai? Call 9876543210",
    "Anyone interested to buy? I have a client selling 2BHK in Dubai Marina",
    "We have 2 BHK and 3 BHK ready to move in Business Bay, interested people message",
    "Golden visa related details???"])
def test_renters_sellers_adverts_and_non_property_purchases_never_qualify(text):
    p = run(yt(text))
    assert p["status"] == "reject", (text, p["reason"])


def test_a_seller_is_only_someone_selling_their_own():
    text = "i live in Dubai i own a apartment, he is a sales guy of a developer trying to sell"
    assert "NEG_sell" not in textsig.markers(text) and "NEG_sell" in textsig.markers("I want to sell my flat in JVC")
    assert "advice_giver" not in textsig.markers("Emi how much. If you can share") and "advice_giver" in textsig.markers("you can get 8% there")


@pytest.mark.parametrize("text", ["Guys Indian properties are best, just look beyond the overpriced metros. " * 3 + "How is this fair?",
                                  "Nicee price", "വില്ല വാങ്ങിയ താണോ? അതൊ rent ano?", "This video is totally wrong details."])
def test_commentary_that_mentions_a_price_is_not_an_enquiry(text):
    assert "enquiry" not in textsig.markers(text)


def test_a_reply_to_another_viewer_is_discussion_even_without_an_at_mention():
    s = yt("Enna bro? Is it good to buy property there?")
    s["kind"], s["reply_to"] = "reply", "viewer"
    assert run(s)["status"] == "reject" and "another commenter" in run(s)["reason"]
    s = yt("Enna bro? Is it good to buy property there?")
    s["kind"], s["reply_to"] = "reply", "creator"                      # answering the creator is still their own enquiry
    assert run(s)["status"] == "needs_validation"


def test_a_video_about_another_emirate_does_not_make_its_viewers_dubai_prospects():
    s = yt("Emi how much per month?", lang="ml")
    s["off_target"] = "the villa is in Ajman"
    p = run(s)
    assert p["status"] == "reject" and "not about Dubai property" in p["reason"] and "target_dubai" not in p["markers"]
    s = yt("Nice video. I want to buy a flat in Dubai Marina, what is the down payment?", lang="ml")
    s["off_target"] = "the villa is in Ajman"
    assert run(s)["status"] == "needs_validation"                      # their own words point to Dubai


def test_an_existing_owner_with_no_sign_of_buying_again_needs_a_stated_south_india_base():
    assert run(yt("I purchased a property through his company, he is a man of his words"))["status"] == "reject"
    p = run(yt("I am living in Chennai. I bought a flat there last year"))
    assert p["status"] == "needs_validation" and any("past purchase" in u for u in p["unverified"])


def test_only_a_stated_home_is_shown_as_the_persons_city():
    p = run(yt("Is Dubai better than Hyderabad for a 2BHK? What is the down payment?", lang="te"))
    row = qualify.to_row(p)
    assert p["loc"]["tier"] == "mention" and (row["city"], row["state"]) == ("unknown", "unknown")
    assert row["inferred_region"] == "Hyderabad, Telangana (place mentioned, not stated as home)" and row["meets_both_tests"] == "no"
    row = qualify.to_row(run(yt("I'm in Kochi. How can I buy property in Dubai?", lang="ml")))
    assert (row["city"], row["state"], row["meets_both_tests"]) == ("Kochi", "Kerala", "yes")
    assert qualify.to_row(run(yt("price?")))["meets_both_tests"] == "no"


def test_someone_who_says_they_are_in_india_is_not_described_as_possibly_in_the_gulf():
    p = run(yt("How to invest frm india"))
    assert any("they say they are in India" in u for u in p["unverified"]) and not any("incl. the Gulf" in u for u in p["unverified"])
    assert any("incl. the Gulf" in u for u in run(yt("How can I buy a flat?"))["unverified"])


def test_shortlist_ranks_forward_intent_with_specifics_above_bare_questions_and_owners():
    def rank(text, **kw):
        return qualify.rank_key(run(yt(text, **kw)))
    both = rank("I'm in Chennai. I want to invest, please guide")
    specific = rank("I want to buy a 1BHK, my budget is 60 lakhs")
    bare = rank("How to invest?")
    question = rank("How much down payment?")
    owner_here = rank("I am living in Chennai. I bought a flat there")
    stale = rank("I want to buy a 1BHK, my budget is 60 lakhs", date="2025-02-01")
    assert both > specific > bare > question and both > owner_here > question and specific > stale
