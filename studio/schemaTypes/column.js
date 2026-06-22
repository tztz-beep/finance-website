import { defineField, defineType } from 'sanity'

export default defineType({
  name: 'column',
  title: 'טור מקצועי',
  type: 'document',
  fields: [
    defineField({
      name: 'title',
      title: 'כותרת הטור',
      type: 'string',
      validation: (Rule) => Rule.required(),
    }),
    defineField({
      name: 'slug',
      title: 'קישור ייחודי (Slug)',
      type: 'slug',
      options: { source: 'title' },
    }),
    // השדה הארכיטקטוני החדש: מנוע הניתוב הקטגוריאלי
    defineField({
      name: 'category',
      title: 'קטגוריית הטור (שיוך לעמוד באתר)',
      type: 'string',
      options: {
        list: [
          { title: 'ייעוץ וניהול השקעות', value: 'investments' },
          { title: 'ייעוץ וליווי פנסיוני', value: 'pension' },
          { title: 'תכנון מס ופרישה', value: 'tax' },
          { title: 'קופות גמל והשתלמות', value: 'funds' }
        ],
        layout: 'radio' // מציג את האפשרויות ככפתורי סימון נקיים וקריאים
      },
      validation: (Rule) => Rule.required().error('חובה לבחור קטגוריה כדי שהטור ינותב לעמוד הנכון באתר!'),
    }),
    defineField({
      name: 'publishedAt',
      title: 'תאריך פרסום',
      type: 'datetime',
    }),
    defineField({
      name: 'excerpt',
      title: 'תקציר מנהלים',
      type: 'text',
    }),
    defineField({
      name: 'body',
      title: 'גוף הטור',
      type: 'array',
      of: [{ type: 'block' }],
    }),
  ],
})