'use server'

import { auth } from '@/lib/auth'
import { db } from '@/lib/db'
import { membership, organization } from '@/lib/db/schema'
import { headers } from 'next/headers'
import { eq } from 'drizzle-orm'

export async function ensureWorkspace() {
  const session = await auth.api.getSession({ headers: await headers() })
  if (!session?.user) throw new Error('Unauthorized')
  const existing = await db.select().from(membership).where(eq(membership.userId, session.user.id)).limit(1)
  if (existing[0]) return existing[0].organizationId
  const organizationId = crypto.randomUUID()
  const slug = `${session.user.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '') || 'aurum'}-${organizationId.slice(0, 6)}`
  await db.insert(organization).values({ id: organizationId, name: `${session.user.name}'s workspace`, slug })
  await db.insert(membership).values({ id: crypto.randomUUID(), organizationId, userId: session.user.id, role: 'owner' })
  return organizationId
}
