PLANS = [(50, 4, 30), (100, 9, 40), (250, 25, 60), (500, 55, 75), (1000, 120, 90), (2500, 325, 120), (5000, 700, 150), (10000, 1500, 180)]
PLAN_NAMES = ["Starter", "Explorer", "Navigator", "Voyager", "Summit", "Horizon", "Zenith", "Apex"]

REWARDS = [
    {"slug": "flagship-smartphone", "title": "Flagship Smartphone", "category": "Gadget", "milestone": 1000000, "image_url": "/img/reward-phone.jpg", "duration": None},
    {"slug": "international-trip", "title": "International Trip", "category": "Travel", "milestone": 5000000, "image_url": "/img/reward-trip.jpg", "duration": "6 nights / 7 days (proposed)"},
    {"slug": "suv", "title": "SUV", "category": "Vehicle", "milestone": 7500000, "image_url": "/img/reward-suv.jpg", "duration": None},
    {"slug": "luxury-car", "title": "Luxury Car", "category": "Vehicle", "milestone": 15000000, "image_url": "/img/reward-car.jpg", "duration": None},
]


def reward_extra(r):
    m = f"{r['milestone']:,}"
    return {
        "description": f"A proposed achievement concept: {r['title']}. This is an unapproved reward concept, not a guaranteed prize. Production campaigns must be independently funded and legally reviewed.",
        "qualification_rules": [f"Illustrative team milestone: {m} in simulated team participation volume.", "Volume counts simulated plan enrollments across five generations.", "Suspended or duplicate accounts are excluded."],
        "eligibility": ["Account in good standing", "Account verification (KYC) completed"],
        "terms": ["Concept only — not an offer.", "Availability, specification and eligibility may change or be withdrawn.", "No cash alternative is implied.", "Subject to legal review before any launch."],
        "redemption": ["Reach the illustrative milestone", "Submit a claim from your dashboard", "Administrator reviews eligibility", "If an approved campaign exists, fulfilment is recorded"],
        "faqs": [{"q": "Is this reward guaranteed?", "a": "No. It is a proposed concept shown for demonstration only."}, {"q": "How is progress measured?", "a": "By simulated team participation volume, which has no monetary value."}],
        "inventory": 10, "expires_at": None, "active": True, "concept": True,
    }


METHODS = [
    {"name": "USDT (TRC20)", "type": "usdt_trc20", "network": "TRON (TRC20)", "currency": "USDT", "address": "TXyzDEMOaddressDoNotSend1234567890", "min_amount": 1000, "max_amount": 1000000,
     "instructions": "TEST MODE. Send only USDT on the TRON (TRC20) network. Enter the 64-character transaction hash as your reference."},
    {"name": "USDT (BEP20)", "type": "usdt_bep20", "network": "BNB Smart Chain (BEP20)", "currency": "USDT", "address": "0xDEMO000000000000000000000000000000000000", "min_amount": 1000, "max_amount": 1000000,
     "instructions": "TEST MODE. Send only USDT on BNB Smart Chain (BEP20). Enter the 0x-prefixed transaction hash as your reference."},
]


def legal(title, paras):
    return {"title": title, "body": paras}


CONTENT = {
    "hero": {"headline": "One Platform. Complete Financial Account Management.",
             "description": "Explore participation simulations, manage your account, understand your team network, and follow every transaction from one secure dashboard.",
             "disclaimer": "DEMO MODE: All plans, coins and earnings shown are simulated and hypothetical. They are not guaranteed, not investment advice and cannot be withdrawn."},
    "banners": [{"text": "Platform is running in DEMO MODE — no real-money participation is accepted.", "active": True}],
    "benefits": [
        {"title": "Transparent transaction history", "text": "Every record is an immutable ledger entry with a running balance.", "icon": "ScrollText"},
        {"title": "Account management", "text": "Profile, sessions, preferences and verification in one place.", "icon": "UserCog"},
        {"title": "Secure verification", "text": "Hashed passwords, optional two-factor authentication and rate limiting.", "icon": "ShieldCheck"},
        {"title": "Team network visualization", "text": "See your five-generation network as a tree or a searchable table.", "icon": "Network"},
        {"title": "Real-time notifications", "text": "In-app inbox, popups and opt-in browser push notifications.", "icon": "BellRing"},
        {"title": "Dedicated support", "text": "Ticketing plus Telegram support for payment questions.", "icon": "LifeBuoy"},
        {"title": "Mobile accessibility", "text": "Every screen is designed for phones, tablets and desktops.", "icon": "Smartphone"},
        {"title": "Detailed activity reports", "text": "Charts and exports built on your real account records.", "icon": "BarChart3"},
    ],
    "how_it_works": ["Create an account.", "Complete account verification.", "Explore demonstration plans.", "View hypothetical outcomes.", "Monitor your simulated dashboard.", "Explore the team and achievement features."],
    "trading": [
        {"title": "Cryptocurrency markets", "text": "Digital assets such as Bitcoin and stablecoins trade 24/7 across many venues.", "risks": "Extreme volatility, exchange insolvency and custody risk, smart-contract failures."},
        {"title": "International financial markets", "text": "Global equities, bonds, currencies and derivatives across major exchanges.", "risks": "Currency risk, leverage losses, geopolitical shocks."},
        {"title": "Asset markets", "text": "Commodities such as gold, energy and agricultural products.", "risks": "Price swings, storage/rollover costs, liquidity gaps."},
        {"title": "Indian financial markets", "text": "NSE/BSE equities, derivatives and government securities regulated by SEBI/RBI.", "risks": "Market losses, F&O leverage, regulatory change."},
        {"title": "Regional markets", "text": "Smaller and emerging-market exchanges.", "risks": "Thin liquidity, wider spreads, counterparty and settlement risk."},
    ],
    "risk_points": ["Volatility: prices can move sharply in either direction.", "Liquidity: you may not be able to exit at the price you expect.", "Market losses: you can lose some or all of the capital you commit.",
                    "Fees: spreads, commissions and network fees reduce results.", "Counterparty risk: brokers, exchanges or custodians can fail.", "No strategy produces consistent guaranteed profits."],
    "faqs": [
        {"q": "How do I register?", "a": "Click Create Account, enter your name, email, mobile number with country code and a password, accept the terms, and optionally add a referral code."},
        {"q": "How does account verification work?", "a": "Submit account verification from your profile. An administrator reviews it."},
        {"q": "What are coins?", "a": "Coins are an internal demonstration unit (1 USD = 100 coins by default). They are not a currency and have no market value."},
        {"q": "What are simulations?", "a": "Plans run a daily illustrative calculation. Results are hypothetical, labelled as such, and never become withdrawable money."},
        {"q": "Which payment methods are supported?", "a": "USDT TRC20 and USDT BEP20 are configured in TEST MODE. No real investment deposits are accepted."},
        {"q": "How does the team structure work?", "a": "People who register with your code are your direct referrals (generation 1). Their referrals form generations 2–5."},
        {"q": "How is my account secured?", "a": "Passwords are hashed with bcrypt, logins are rate limited, sessions can be revoked and you can enable two-factor authentication."},
        {"q": "How do notifications work?", "a": "You receive in-app notifications automatically. Browser push is optional and only enabled after you click Enable Notifications."},
        {"q": "How do I get support?", "a": "Open a support ticket from your dashboard or use the Telegram support button on deposit and withdrawal pages."},
    ],
    "footer": {"about": "A demonstration platform for account management, simulated participation plans and team-network visualization.", "note": "No registration numbers, licenses or performance statistics are claimed."},
    "legal_about": legal("About Us", ["[Business to provide: who operates this platform, its legal entity and jurisdiction.]", "This platform currently runs in DEMO MODE for evaluation only."]),
    "legal_contact": legal("Contact", ["Email: support@example.com", "Phone: [Your phone]", "Address: [Your registered address]"]),
    "legal_support": legal("Support", ["Signed-in users can open support tickets from the dashboard.", "Payment-related questions can also be raised via the Telegram support link on the deposit and withdrawal pages."]),
    "legal_privacy": legal("Privacy Policy", ["We collect the information you provide at registration (name, email, mobile) and technical data needed for security (IP address, session data).", "Team members only see limited, masked information about their downline. Contact details and financial records are never shared with uplines.", "[Business to complete with data-retention, processor and rights information after legal review.]"]),
    "legal_terms": legal("Terms and Conditions", ["The platform is provided in DEMO MODE. Simulated coins and earnings have no monetary value and cannot be withdrawn.", "Users must provide accurate information and may hold only one account.", "[Business to complete after legal review.]"]),
    "legal_risk": legal("Risk Disclosure", ["All plan figures are hypothetical examples, not verified investment performance.", "Trading in any market involves the risk of losing some or all capital. Past or simulated results do not indicate future outcomes.", "Referral-based reward structures can create obligations that exceed incoming funds; the liability analysis tool illustrates this risk."]),
    "legal_refund": legal("Refund Policy", ["In TEST MODE no real payments are accepted. Payment records marked refunded are reversed in the ledger with an offsetting entry.", "[Business to complete before any real-money activation.]"]),
    "legal_complaints": legal("Complaint Resolution", ["Raise a support ticket with category and details. Each ticket is tracked until closed.", "[Business to add escalation contacts and regulator details after approval.]"]),
    "legal_cookies": legal("Cookie Preferences", ["We use strictly necessary httpOnly cookies for authentication sessions.", "Local storage is used to remember your notification prompt choice. No advertising cookies are used."]),
    "legal_company": legal("Company Information", ["[Company legal name, registration number and registered office — to be provided by the business. None are claimed here.]"]),
}
