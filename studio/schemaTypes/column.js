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