from datetime import timedelta

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone


GRADE_MAP = [
    (0.80, 'A', '#4c1'),
    (0.60, 'B', '#97CA00'),
    (0.40, 'C', '#dfb317'),
    (0.20, 'D', '#fe7d37'),
    (0.00, 'E', '#e05d44'),
]

BADGE_SVG_TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20">'
    '<linearGradient id="a" x2="0" y2="100%">'
    '<stop offset="0" stop-color="#bbb" stop-opacity=".1"/>'
    '<stop offset="1" stop-opacity=".1"/>'
    '</linearGradient>'
    '<rect rx="3" width="{width}" height="20" fill="#555"/>'
    '<rect rx="3" x="{label_width}" width="30" height="20" fill="{color}"/>'
    '<path fill="{color}" d="M{label_width} 0h4v20h-4z"/>'
    '<rect rx="3" width="{width}" height="20" fill="url(#a)"/>'
    '<g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,'
    'Verdana,Geneva,sans-serif" font-size="11">'
    '<text x="{label_center}" y="15" fill="#010101" fill-opacity=".3">'
    '{label}</text>'
    '<text x="{label_center}" y="14">{label}</text>'
    '<text x="{grade_center}" y="15" fill="#010101" fill-opacity=".3">'
    '{grade}</text>'
    '<text x="{grade_center}" y="14">{grade}</text>'
    '</g>'
    '</svg>'
)

BADGE_STALE_SVG_TEMPLATE = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20">'
    '<rect rx="3" width="{width}" height="20" fill="#9f9f9f"/>'
    '<g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,'
    'Verdana,Geneva,sans-serif" font-size="11">'
    '<text x="{center}" y="14">{label} N/A</text>'
    '</g></svg>'
)


def get_grade(value):
    """Return (grade_letter, color_hex) for a given 0-1 value."""
    for threshold, grade, color in GRADE_MAP:
        if value >= threshold:
            return grade, color
    return 'E', '#e05d44'


def is_stale(created_at):
    """Return True if created_at is older than BADGE_STALENESS_DAYS."""
    max_age_days = settings.BADGE_STALENESS_DAYS
    if max_age_days is None or max_age_days <= 0:
        return False
    return timezone.now() - created_at > timedelta(days=max_age_days)


def render_badge_svg(label, value):
    """Render a badge SVG for the given label and 0-1 value."""
    grade, color = get_grade(value)
    # Approximate width: 7px per char for label + 30px for grade box
    label_width = max(len(label) * 7 + 10, 60)
    width = label_width + 30
    label_center = label_width // 2
    grade_center = label_width + 15

    svg = BADGE_SVG_TEMPLATE.format(
        width=width,
        label_width=label_width,
        label_center=label_center,
        grade_center=grade_center,
        color=color,
        grade=grade,
        label=label,
    )
    return HttpResponse(svg, content_type="image/svg+xml")


def render_stale_badge_svg(label):
    """Render a N/A (stale/missing) badge SVG."""
    text = f"{label} N/A"
    width = max(len(text) * 7 + 10, 100)
    center = width // 2

    svg = BADGE_STALE_SVG_TEMPLATE.format(
        width=width,
        center=center,
        label=label,
    )
    return HttpResponse(svg, content_type="image/svg+xml")

