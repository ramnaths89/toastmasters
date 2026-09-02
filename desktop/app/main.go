// Toastmasters Tools desktop wrap. Serves the embedded HTML tools on
// 127.0.0.1 and opens them in a native window. Windows uses Edge WebView2;
// other OSes (and WebView2 failure) fall back to Chrome/Edge --app. file://
// is not used.
//
// The same source builds two apps. build.py stages a different web/ tree per
// variant and sets title, appID and prefAddr with -ldflags "-X main.title=…":
//
//	hub   — all four tools behind index.html          (ToastmastersTools.exe)
//	sheet — the programme sheet builder as the root  (ProgrammeSheet.exe)
//
// appID names the per-app WebView2 / browser profile folder, so the two apps
// keep separate localStorage; prefAddr gives each a stable origin of its own.
package main

import (
	"embed"
	"flag"
	"fmt"
	"io/fs"
	"net"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"
)

//go:embed all:web
var webFS embed.FS

var (
	title    = "Toastmasters Tools"
	appID    = "ToastmastersTools"
	version  = "0.48.0"
	prefAddr = "127.0.0.1:8765"
)

func main() {
	serveOnly := flag.Bool("serve", false, "serve on 127.0.0.1 and print the URL; do not open a window")
	flag.Parse()

	url, ln, err := startServer()
	if err != nil {
		fail("Could not start the local server:\n" + err.Error())
		os.Exit(1)
	}
	defer ln.Close()

	if *serveOnly {
		fmt.Fprintf(os.Stderr, "Serving %s\nStop with Ctrl+C\n", url)
		waitSignal()
		return
	}

	if err := openWindow(url); err != nil {
		fail("Could not open " + title + ":\n" + err.Error() + "\n\nThe page is at:\n" + url)
		os.Exit(1)
	}
}

func startServer() (url string, ln net.Listener, err error) {
	sub, err := fs.Sub(webFS, "web")
	if err != nil {
		return "", nil, err
	}
	mux := http.NewServeMux()
	mux.Handle("/", noCache(http.FileServer(http.FS(sub))))

	ln, err = net.Listen("tcp", prefAddr)
	if err != nil {
		ln, err = net.Listen("tcp", "127.0.0.1:0")
		if err != nil {
			return "", nil, err
		}
	}
	go http.Serve(ln, mux)
	return "http://" + ln.Addr().String() + "/", ln, nil
}

func noCache(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-store")
		if strings.HasSuffix(r.URL.Path, ".svg") {
			w.Header().Set("Content-Type", "image/svg+xml")
		}
		next.ServeHTTP(w, r)
	})
}

func waitSignal() {
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	<-c
}
