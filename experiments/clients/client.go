// Go client. Usage: client HOST PORT MODE DURATION_S INTERVAL_MS CONNECT_TIMEOUT|none CAP_S
// Resolver choice comes from GODEBUG=netdns=go or cgo. Every dial attempt is logged through Dialer.Control.
package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"strconv"
	"strings"
	"syscall"
	"time"
)

func out(m map[string]interface{}) { b, _ := json.Marshal(m); fmt.Println(string(b)) }

func main() {
	a := os.Args[1:]
	host, port, mode := a[0], a[1], a[2]
	dur, _ := strconv.ParseFloat(a[3], 64)
	iv, _ := strconv.ParseFloat(a[4], 64)
	cap, _ := strconv.ParseFloat(a[6], 64)
	d := &net.Dialer{Timeout: 30 * time.Second, // the value http.DefaultTransport uses
		Control: func(network, address string, c syscall.RawConn) error {
			out(map[string]interface{}{"t": time.Now().UnixMilli(), "attempt": address})
			return nil
		}}
	if a[5] != "none" {
		v, _ := strconv.ParseFloat(a[5], 64)
		d.Timeout = time.Duration(v * float64(time.Second))
	}
	cl := &http.Client{Transport: &http.Transport{DisableKeepAlives: true, DialContext: d.DialContext}, Timeout: time.Duration(cap * float64(time.Second))}
	end := time.Now().Add(time.Duration(dur * float64(time.Second)))
	for {
		t := time.Now()
		r, err := cl.Get("http://" + host + ":" + port + "/")
		m := map[string]interface{}{"t": t.UnixMilli(), "ms": time.Since(t).Milliseconds()}
		if err != nil {
			m["err"] = "error"
			if strings.Contains(err.Error(), "Client.Timeout") {
				m["err"] = "cap"
			}
		} else {
			b, _ := io.ReadAll(r.Body)
			r.Body.Close()
			m["body"] = strings.TrimSpace(string(b))
		}
		out(m)
		if mode == "once" || time.Now().After(end) {
			return
		}
		time.Sleep(time.Until(t.Add(time.Duration(iv * float64(time.Millisecond)))))
	}
}
