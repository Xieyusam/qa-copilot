export async function request(url: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem('token')
  const headers = new Headers(options.headers || {})
  
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const finalOptions: RequestInit = {
    ...options,
    headers,
  }

  const response = await fetch(url, finalOptions)

  if (response.status === 401) {
    // Token expired or invalid
    localStorage.removeItem('token')
    window.location.href = '/login'
  }
  
  if (response.status === 403) {
    // Forbidden, user is not admin
    window.location.href = '/'
  }

  return response
}
