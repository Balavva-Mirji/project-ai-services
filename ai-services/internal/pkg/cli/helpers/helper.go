package helpers

import (
	"fmt"
	"io/fs"
	"slices"
	"strings"
	"text/template"

	"github.com/project-ai-services/ai-services/assets"
)

func FetchApplicationTemplatesNames() ([]string, error) {
	apps := []string{}

	err := fs.WalkDir(assets.ApplicationFS, "applications", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}

		// Templates Pattern :- "assets/applications/<AppName>/*.yaml.tmpl"
		parts := strings.Split(path, "/")

		if len(parts) >= 3 {
			appName := parts[1]
			if slices.Contains(apps, appName) {
				return nil
			}
			apps = append(apps, appName)
		}
		return nil
	})
	if err != nil {
		return nil, err
	}

	return apps, nil
}

func LoadAllTemplates() (map[string]*template.Template, error) {
	tmpls := make(map[string]*template.Template)

	err := fs.WalkDir(assets.ApplicationFS, "applications", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() || !strings.HasSuffix(d.Name(), ".tmpl") {
			return nil
		}

		t, err := template.ParseFS(assets.ApplicationFS, path)
		if err != nil {
			return fmt.Errorf("parse %s: %w", path, err)
		}
		tmpls[path] = t
		return nil
	})
	return tmpls, err
}
