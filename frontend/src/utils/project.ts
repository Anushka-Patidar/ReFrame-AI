import { api } from '../lib/api'
import type { DesignVersion, Room } from '../types/api'

export async function getLatestRoomAndDesign(token: string): Promise<{
  room: Room | null
  design: DesignVersion | null
}> {
  const rooms = await api.listRooms(token)
  if (rooms.length === 0) {
    return { room: null, design: null }
  }

  const sortedRooms = [...rooms].sort((left, right) =>
    right.created_at.localeCompare(left.created_at),
  )
  const room = sortedRooms[0]
  const designs = await api.listDesigns(token, room.id)
  const design =
    designs.length > 0
      ? [...designs].sort((left, right) => right.created_at.localeCompare(left.created_at))[0]
      : null

  return { room, design }
}
