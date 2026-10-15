'use server'

import { auth } from '@/lib/auth'
import { db } from '@/lib/db'
import { auditEvent, loanApplication, membership, organization } from '@/lib/db/schema'
import { headers } from 'next/headers'
import { revalidatePath } from 'next/cache'
import { eq } from 'drizzle-orm'

async function getUser() {
  const session = await auth.api.getSession({ headers: await headers() })
  if (!session?.user) throw new Error('Unauthorized')
  return session.user
}

export async function createLoanApplication(input: { customerName: string; requestedAmount: number; tenureMonths: number; purpose?: string }) {
  const user = await getUser()
  if (!input.customerName.trim() || input.requestedAmount <= 0 || input.tenureMonths <= 0) throw new Error('Invalid application details')
  const member = await db.select().from(membership).where(eq(membership.userId, user.id)).limit(1)
  let organizationId = member[0]?.organizationId
  if (!organizationId) {
    organizationId = crypto.randomUUID()
    const slug = `${user.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '') || 'aura'}-${organizationId.slice(0, 6)}`
    await db.insert(organization).values({ id: organizationId, name: `${user.name}'s workspace`, slug })
    await db.insert(membership).values({ id: crypto.randomUUID(), organizationId, userId: user.id, role: 'owner' })
  }
  const id = crypto.randomUUID()
  const applicationNumber = `AUR-${new Date().getFullYear()}-${Math.floor(10000 + Math.random() * 89999)}`
  await db.insert(loanApplication).values({ id, organizationId, createdBy: user.id, applicationNumber, customerName: input.customerName.trim(), requestedAmount: String(input.requestedAmount), tenureMonths: input.tenureMonths, purpose: input.purpose?.trim() || null })
  await db.insert(auditEvent).values({ id: crypto.randomUUID(), organizationId, actorId: user.id, entityType: 'loan_application', entityId: id, action: 'created', metadata: { applicationNumber } })
  revalidatePath('/')
  return { id, applicationNumber }
}
