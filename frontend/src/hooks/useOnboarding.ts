import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'

export type OnboardingStep = {
  id: string
  title: string
  description: string
  complete: boolean
  path: string
  cta: string
}

const analyzedStatuses = new Set(['ANALYZED', 'READY', 'PUBLISHED'])

export function useOnboarding() {
  const storesQuery = useQuery({ queryKey: ['stores'], queryFn: api.stores.list })
  const productsQuery = useQuery({ queryKey: ['products'], queryFn: api.products.list })
  const campaignsQuery = useQuery({ queryKey: ['campaigns'], queryFn: api.campaigns.list })

  const stores = storesQuery.data ?? []
  const products = productsQuery.data ?? []
  const campaigns = campaignsQuery.data ?? []

  const connectedStore = stores.find((store: any) => store.status === 'CONNECTED')
  const firstProduct = products[0]
  const analyzedProduct = products.find((product: any) => analyzedStatuses.has(product.status))
  const firstCampaign = campaigns[0]
  const publishedCampaign = campaigns.find((campaign: any) => campaign.status === 'PUBLISHED')

  const steps: OnboardingStep[] = [
    {
      id: 'account',
      title: 'Create your account',
      description: 'Your Velnio workspace is ready.',
      complete: true,
      path: '/settings',
      cta: 'View workspace',
    },
    {
      id: 'store',
      title: 'Connect your store',
      description: 'Connect the store where you want to launch and publish products.',
      complete: Boolean(connectedStore),
      path: '/stores',
      cta: connectedStore ? 'View store' : 'Connect store',
    },
    {
      id: 'product',
      title: 'Add your first product',
      description: 'Create or import the product you want Velnio to turn into a campaign.',
      complete: products.length > 0,
      path: firstProduct ? `/products/${firstProduct.id}` : '/products/new',
      cta: firstProduct ? 'Open product' : 'Add product',
    },
    {
      id: 'analysis',
      title: 'Analyze the product',
      description: 'Use AI analysis to validate the opportunity before building the campaign.',
      complete: Boolean(analyzedProduct),
      path: analyzedProduct
        ? `/products/${analyzedProduct.id}`
        : firstProduct
          ? `/products/${firstProduct.id}`
          : '/products/new',
      cta: analyzedProduct ? 'View analysis' : firstProduct ? 'Analyze product' : 'Add product first',
    },
    {
      id: 'campaign',
      title: 'Create your first campaign',
      description: 'Choose the product, audience and market, then generate angles, offer and landing.',
      complete: campaigns.length > 0,
      path: firstCampaign ? `/campaigns/${firstCampaign.id}` : '/campaigns/new',
      cta: firstCampaign ? 'Open campaign' : 'Create campaign',
    },
    {
      id: 'publish',
      title: 'Publish your campaign',
      description: 'Finish the launch assets and publish the campaign to your connected store.',
      complete: Boolean(publishedCampaign),
      path: publishedCampaign
        ? `/campaigns/${publishedCampaign.id}`
        : firstCampaign
          ? `/campaigns/${firstCampaign.id}`
          : '/campaigns/new',
      cta: publishedCampaign ? 'View published campaign' : firstCampaign ? 'Finish campaign' : 'Create campaign first',
    },
  ]

  const completed = steps.filter((step) => step.complete).length
  const nextStep = steps.find((step) => !step.complete) ?? null
  const isComplete = completed === steps.length

  return {
    steps,
    completed,
    total: steps.length,
    progress: Math.round((completed / steps.length) * 100),
    nextStep,
    isComplete,
    isLoading: storesQuery.isLoading || productsQuery.isLoading || campaignsQuery.isLoading,
    isError: storesQuery.isError || productsQuery.isError || campaignsQuery.isError,
  }
}
