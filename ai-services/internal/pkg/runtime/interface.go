package runtime

import "io"

type Runtime interface {
	ListImages() ([]string, error)
	ListPods(filters map[string][]string) (any, error)
	CreatePodFromTemplate(filePath string, params map[string]any) error
	CreatePod(body io.Reader) error
	DeletePod(id string, force *bool) error
}
