# utils.py

from decimal import Decimal
from .models import LessonCompletion

def prepare_course_detail_context(course, enrollment):
    lessons = course.lessons.all()
    lessons_with_completion = []

    # Get completion status for each lesson
    for lesson in lessons:
        completion = None
        if enrollment:
            completion = LessonCompletion.objects.filter(
                enrollment=enrollment, 
                lesson=lesson
            ).first()

        lessons_with_completion.append({
            'lesson': lesson,
            'completion': completion,
        })

    tax_rate = Decimal('0.15')  # Example tax rate
    tax = course.price * tax_rate
    total_price = course.price + tax

    context = {
        'course': course,
        'tax': tax,
        'total_price': total_price,
        'enrollment': enrollment,
        'lessons_with_completion': lessons_with_completion,
        'progress_percentage': enrollment.get_progress_percentage() if enrollment else 0,
    }
    return context
