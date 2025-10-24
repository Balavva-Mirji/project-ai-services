package application

import (
	"github.com/spf13/cobra"
)

// ApplicationCmd represents the application command
var ApplicationCmd = &cobra.Command{
	Use:   "application",
	Short: "Deploy and monitor the applications",
	Long:  `The application command helps you deploy and monitor the applications`,
}

func init() {
	ApplicationCmd.AddCommand(templatesCmd)
	ApplicationCmd.AddCommand(createCmd)
	ApplicationCmd.AddCommand(psCmd)
	ApplicationCmd.AddCommand(deleteCmd)
}
