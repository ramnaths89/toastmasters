//go:build windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"syscall"
	"unsafe"

	"github.com/jchv/go-webview2"
	"golang.org/x/sys/windows"
)

func openWindow(url string) error {
	cache, err := os.UserCacheDir()
	if err != nil {
		cache = os.TempDir()
	}
	dataPath := filepath.Join(cache, appID, "webview2")
	_ = os.MkdirAll(dataPath, 0755)

	w := webview2.NewWithOptions(webview2.WebViewOptions{
		Debug:     false,
		AutoFocus: true,
		DataPath:  dataPath,
		WindowOptions: webview2.WindowOptions{
			Title:  title,
			Width:  1440,
			Height: 900,
			Center: true,
		},
	})
	if w == nil {
		return openBrowserApp(url)
	}
	defer w.Destroy()
	w.SetSize(1440, 900, webview2.HintNone)
	w.Navigate(url)
	w.Run()
	return nil
}

func openBrowserApp(url string) error {
	browser := findWindowsBrowser()
	if browser == "" {
		return fmt.Errorf("Edge or Chrome was not found. Install Microsoft Edge, then run this again")
	}
	cache, err := os.UserCacheDir()
	if err != nil {
		cache = os.TempDir()
	}
	profile := filepath.Join(cache, appID, "chrome-profile")
	_ = os.MkdirAll(profile, 0755)
	cmd := exec.Command(browser,
		"--app="+url,
		"--user-data-dir="+profile,
		"--no-first-run",
		"--no-default-browser-check",
	)
	cmd.SysProcAttr = &syscall.SysProcAttr{HideWindow: true}
	return cmd.Run()
}

func findWindowsBrowser() string {
	candidates := []string{
		filepath.Join(os.Getenv("ProgramFiles(x86)"), "Microsoft", "Edge", "Application", "msedge.exe"),
		filepath.Join(os.Getenv("ProgramFiles"), "Microsoft", "Edge", "Application", "msedge.exe"),
		filepath.Join(os.Getenv("ProgramFiles"), "Google", "Chrome", "Application", "chrome.exe"),
		filepath.Join(os.Getenv("ProgramFiles(x86)"), "Google", "Chrome", "Application", "chrome.exe"),
		filepath.Join(os.Getenv("LocalAppData"), "Google", "Chrome", "Application", "chrome.exe"),
	}
	for _, p := range candidates {
		if p == "" {
			continue
		}
		if st, err := os.Stat(p); err == nil && !st.IsDir() {
			return p
		}
	}
	return ""
}

func fail(msg string) {
	mod := windows.NewLazySystemDLL("user32.dll")
	proc := mod.NewProc("MessageBoxW")
	caption, _ := windows.UTF16PtrFromString(title)
	text, _ := windows.UTF16PtrFromString(msg)
	proc.Call(0, uintptr(unsafe.Pointer(text)), uintptr(unsafe.Pointer(caption)), 0x10)
}
