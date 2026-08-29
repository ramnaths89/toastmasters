//go:build !windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"os/user"
	"path/filepath"
	"runtime"
)

func openWindow(url string) error {
	return openBrowserApp(url)
}

func openBrowserApp(url string) error {
	browser := findBrowser()
	if browser == "" {
		return fmt.Errorf("install Chrome, Chromium or Edge, then run this again")
	}
	home := os.TempDir()
	if u, err := user.Current(); err == nil && u.HomeDir != "" {
		home = u.HomeDir
	}
	profile := filepath.Join(home, ".cache", "ToastmastersTools", "chrome-profile")
	_ = os.MkdirAll(profile, 0755)
	cmd := exec.Command(browser,
		"--app="+url,
		"--user-data-dir="+profile,
		"--no-first-run",
		"--no-default-browser-check",
	)
	return cmd.Run()
}

func findBrowser() string {
	names := []string{
		"google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
		"microsoft-edge", "msedge",
	}
	if runtime.GOOS == "darwin" {
		mac := []string{
			"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
			"/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
		}
		for _, p := range mac {
			if st, err := os.Stat(p); err == nil && !st.IsDir() {
				return p
			}
		}
	}
	for _, n := range names {
		if p, err := exec.LookPath(n); err == nil {
			return p
		}
	}
	return ""
}

func fail(msg string) {
	fmt.Fprintln(os.Stderr, msg)
}
