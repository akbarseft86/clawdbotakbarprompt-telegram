#!/usr/bin/env python3
"""Import missing prompts from CSV into Notion via telegram_middleware."""
import asyncio
import sys
sys.path.insert(0, "/root/.openclaw/scripts")
from telegram_middleware import load_notion_prompts, save_prompt_to_notion, notion_prompts_cache

MISSING_PROMPTS = [
    {
        "title": "2. Full Tailwind + HTML Skeleton from Screenshot",
        "category": "Landing Page & Website",
        "content": (
            "2. Full Tailwind + HTML Skeleton from Screenshot\n\n"
            "You are an expert frontend developer who specializes in pixel-perfect Tailwind CSS conversions.\n\n"
            "Use this screenshot as reference: [upload or describe]\n\n"
            "Build the complete HTML + Tailwind CSS structure:\n"
            "- Semantic HTML5 (header, main, section, footer)\n"
            "- Mobile-first responsive design\n"
            "- Use modern Tailwind classes (no custom CSS unless necessary)\n"
            "- Include placeholder images (unsplash links) and icons (heroicons or lucide)\n"
            "- Hero, features, testimonials, CTA, footer\n"
            "- Clean, commented code\n"
            "- Dark mode support (optional class)\n\n"
            "Output the full code in one block."
        )
    },
    {
        "title": "3. Copywriting & Headline Upgrade from Screenshot",
        "category": "Landing Page & Website",
        "content": (
            "3. Copywriting & Headline Upgrade from Screenshot\n\n"
            "You are a top direct-response copywriter who 2x's conversion rates.\n\n"
            "Screenshot reference: [upload]\n\n"
            "Rewrite and upgrade every piece of copy visible:\n"
            "- Main headline (make it 30% stronger)\n"
            "- Subheadline (more benefit-focused)\n"
            "- Bullet points / features (punchier, outcome-driven)\n"
            "- CTA buttons (urgency + specificity)\n"
            "- Testimonial blurbs (more believable & emotional)\n"
            "- Any micro-copy (trust badges, guarantees)\n\n"
            "Give 3 headline variations and 2 full copy upgrades."
        )
    },
    {
        "title": "4. Hero Section Perfection Prompt",
        "category": "Landing Page & Website",
        "content": (
            "4. Hero Section Perfection Prompt\n\n"
            "You are a conversion-obsessed hero section specialist.\n\n"
            "From this screenshot: [upload]\n\n"
            "Build the strongest possible hero section:\n"
            "- Headline + subheadline (2 versions: bold + curiosity)\n"
            "- Primary CTA button text + color + hover effect\n"
            "- Background style (gradient, image, subtle animation idea)\n"
            "- Trust elements (logos, \"as seen in\", rating stars)\n"
            "- Visual hierarchy notes (what's biggest, what fades)\n\n"
            "Output ready-to-paste Tailwind classes + copy."
        )
    },
    {
        "title": "6. Color Palette & Typography Extractor",
        "category": "Landing Page & Website",
        "content": (
            "6. Color Palette & Typography Extractor\n\n"
            "You are a design system extractor.\n\n"
            "From this screenshot: [upload]\n\n"
            "Extract and name:\n"
            "- Primary color palette (hex codes: main, accent, neutral, danger/success)\n"
            "- Secondary/supporting colors\n"
            "- Typography stack (font families + weights + sizes for h1, h2, body, button)\n"
            "- Spacing scale (padding/margin pattern)\n"
            "- Border-radius & shadow usage\n\n"
            "Then suggest 2 modern alternatives (darker mode + lighter mode) with hex codes."
        )
    }
]


async def main():
    await load_notion_prompts()
    print("Before import:", len(notion_prompts_cache), "prompts")

    for p in MISSING_PROMPTS:
        success, result = await save_prompt_to_notion(
            p["title"], p["content"], category=p["category"]
        )
        if success:
            print("OK:", p["title"][:50], "-> slug=" + result)
        else:
            print("FAIL:", p["title"][:50], "->", result)

    print("After import:", len(notion_prompts_cache), "prompts")


if __name__ == "__main__":
    asyncio.run(main())
