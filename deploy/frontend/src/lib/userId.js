export function getUserId() {
  let id = localStorage.getItem('mechai_user_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('mechai_user_id', id)
  }
  return id
}
