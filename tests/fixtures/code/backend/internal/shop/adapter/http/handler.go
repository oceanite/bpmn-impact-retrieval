package http

type Handler struct{}

func (h Handler) Register(r Router) {
	r.Post("/orders/{id}/confirm", h.confirm)
	r.Get("/deliveries", h.listDeliveries)
}

func (h Handler) confirm(w Writer, r *Request) {}

func (h Handler) listDeliveries(w Writer, r *Request) {}
