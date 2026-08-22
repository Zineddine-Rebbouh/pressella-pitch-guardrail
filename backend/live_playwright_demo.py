import asyncio
from playwright.async_api import async_playwright

async def run_live_demo():
    async with async_playwright() as p:
        # Launch Chromium in HEADED mode (visible to the user on their screen)
        browser = await p.chromium.launch(headless=False, slow_mo=800)
        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        print("Navigating to http://localhost:3000...")
        await page.goto("http://localhost:3000")
        await page.wait_for_load_state("networkidle")

        print("Filling out form fields...")
        # Fill Company Name
        company_input = page.locator("input[name='company'], input[placeholder*='Company'], input[id*='company']").first
        if await company_input.count() > 0:
            await company_input.fill("NovaSpark AI")
        
        # Fill inputs on page
        inputs = await page.locator("input[type='text'], textarea").all()
        print(f"Found {len(inputs)} form inputs/textareas")
        
        # Look for explicit labels or placeholders
        for inp in inputs:
            placeholder = (await inp.get_attribute("placeholder") or "").lower()
            name = (await inp.get_attribute("name") or "").lower()
            id_attr = (await inp.get_attribute("id") or "").lower()
            
            if any(k in placeholder or k in name or k in id_attr for k in ["company", "startup"]):
                await inp.fill("NovaSpark AI")
            elif any(k in placeholder or k in name or k in id_attr for k in ["industry", "sector"]):
                await inp.fill("B2B SaaS")
            elif any(k in placeholder or k in name or k in id_attr for k in ["target", "audience", "contact", "role"]):
                await inp.fill("Series A startup founders")
            elif any(k in placeholder or k in name or k in id_attr for k in ["value", "prop", "talking", "data"]):
                await inp.fill("Automates investor outreach with personalized AI-generated pitch emails, saving 10 hours per week")
            elif any(k in placeholder or k in name or k in id_attr for k in ["tone"]):
                await inp.fill("Professional yet conversational")
            elif any(k in placeholder or k in name or k in id_attr for k in ["goal", "campaign"]):
                await inp.fill("Introduce NovaSpark AI and schedule a demo")
            elif any(k in placeholder or k in name or k in id_attr for k in ["differentiator", "key", "points"]):
                await inp.fill("Real-time personalization, SOC2 compliant, 3x higher open rates than manual outreach")

        # Take a pause so user can see filled form
        await asyncio.sleep(2)

        print("Submitting form...")
        submit_btn = page.locator("button[type='submit'], button:has-text('Generate'), button:has-text('Submit')").first
        if await submit_btn.count() > 0:
            await submit_btn.click()

        print("Waiting for response/draft generation (up to 40s)...")
        await page.wait_for_timeout(15000)

        # Look for verify button
        verify_btn = page.locator("button:has-text('Verify'), button:has-text('Run Guardrails')").first
        if await verify_btn.count() > 0 and await verify_btn.is_visible():
            print("Clicking Verify button...")
            await verify_btn.click()
            await page.wait_for_timeout(10000)

        # Look for approve button
        approve_btn = page.locator("button:has-text('Approve')").first
        if await approve_btn.count() > 0 and await approve_btn.is_visible():
            print("Clicking Approve button...")
            await approve_btn.click()
            await page.wait_for_timeout(3000)

            print("Testing immutability by clicking Approve again...")
            if await approve_btn.is_visible() and await approve_btn.is_enabled():
                await approve_btn.click()
                await page.wait_for_timeout(3000)

        print("Demo completed. Keeping browser open for 10 seconds for user view...")
        await asyncio.sleep(10)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_live_demo())
