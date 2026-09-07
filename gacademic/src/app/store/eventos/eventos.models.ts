// Alinhado com app/schemas/eventos.py.

export interface EventoFoto {
  id: string;
  url: string; // data URI — ver storage.py
}

export interface Evento {
  id: string;
  titulo: string;
  data: string; // "YYYY-MM-DD"
  descricao: string | null;
  publicado: boolean;
  fotos: EventoFoto[];
}
