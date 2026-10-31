import { useMutation } from '@tanstack/react-query'
import { TokenStorage } from '@/utils/tokenStorage'

interface AccountSession {
  userId: string
  version: number
}

function isCurrentSession(session: AccountSession | null | undefined): session is AccountSession {
  return !!session && session.version === TokenStorage.getVersion()
}

function assertCurrentSession(
  session: AccountSession | null | undefined
): asserts session is AccountSession {
  if (!isCurrentSession(session)) throw new DOMException('Session changed', 'AbortError')
}

/** Keep mutation results, notifications, and awaiting callers inside their initiating session. */
export function useAccountMutation<TData, TVariables>(
  userId: string | undefined,
  action: (variables: TVariables) => Promise<TData>,
  callbacks: {
    onSuccess: (data: TData, userId: string) => void
    onError: (error: Error) => void
  }
) {
  const session = userId ? { userId, version: TokenStorage.getVersion() } : null
  const mutation = useMutation({
    onMutate: ({ session }) => {
      assertCurrentSession(session)
      return session
    },
    mutationFn: async ({ session, variables }: { session: AccountSession; variables: TVariables }) => {
      assertCurrentSession(session)
      try {
        return await action(variables)
      } finally {
        // Discard both late responses and late errors, including secret key data.
        assertCurrentSession(session)
      }
    },
    onSuccess: (data, _variables, owner) => {
      assertCurrentSession(owner)
      callbacks.onSuccess(data, owner.userId)
    },
    onError: (error, _variables, owner) => {
      if (isCurrentSession(owner)) callbacks.onError(error)
    },
    onSettled: (_data, error, _variables, owner) => {
      if (!error) assertCurrentSession(owner)
    },
  })

  return {
    isPending: mutation.isPending,
    mutateAsync: async (variables: TVariables): Promise<TData> => {
      assertCurrentSession(session)
      const data = await mutation.mutateAsync({ session, variables })
      // React Query awaits callbacks before resolving; recheck before the UI continuation.
      assertCurrentSession(session)
      return data
    },
  }
}
