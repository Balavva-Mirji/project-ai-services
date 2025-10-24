package application

import (
	"bytes"
	"errors"
	"fmt"
	"slices"

	"github.com/spf13/cobra"

	"github.com/project-ai-services/ai-services/internal/pkg/cli/helpers"
	"github.com/project-ai-services/ai-services/internal/pkg/runtime/podman"
)

var templateName string

var createCmd = &cobra.Command{
	Use:   "create [name]",
	Short: "Deploys an application",
	Long: `Deploys an application with the provided application name based on the template
		Arguments
		- [name]: Application name (Required)
	`,
	Args: func(cmd *cobra.Command, args []string) error {
		if len(args) < 1 {
			return errors.New("you must provide an application name")
		}
		return nil
	},
	RunE: func(cmd *cobra.Command, args []string) error {
		appName := args[0]

		cmd.Printf("Creating application '%s' using template '%s'\n", appName, templateName)

		// Fetch all the application Template names
		appTemplateNames, err := helpers.FetchApplicationTemplatesNames()
		if err != nil {
			return fmt.Errorf("failed to list templates: %w", err)
		}

		if !slices.Contains(appTemplateNames, templateName) {
			return errors.New("provided template name is wrong. Please provide a valid template name")
		}

		tmpls, err := helpers.LoadAllTemplates()
		if err != nil {
			return fmt.Errorf("failed to parse the templates: %w", err)
		}

		params := map[string]any{
			"AppName": appName,
		}

		// podman connectivity
		runtime, err := podman.NewPodmanClient()
		if err != nil {
			return fmt.Errorf("failed to connect to podman: %w", err)
		}

		// Loop through all pod templates, render and run kube play
		cmd.Printf("Total Pod Templates to be processed: %d\n", len(tmpls))
		for name, tmpl := range tmpls {
			cmd.Printf("Processing template: %s...\n", name)

			var rendered bytes.Buffer
			if err := tmpl.Execute(&rendered, params); err != nil {
				return fmt.Errorf("failed to execute template %s: %v", name, err)
			}

			// Wrap the bytes in a bytes.Reader
			reader := bytes.NewReader(rendered.Bytes())

			if err := runtime.CreatePod(reader); err != nil {
				return fmt.Errorf("failed pod creation: %w", err)
			}

			cmd.Printf("Successfully ran podman kube play for %s\n", name)
			cmd.Println("-------")
		}

		// TODO: Wait until all the pods are in Running/ Ready state

		return nil
	},
}

func init() {
	createCmd.Flags().StringVarP(&templateName, "template-name", "t", "", "Template name to use (required)")
	createCmd.MarkFlagRequired("template-name")
}
