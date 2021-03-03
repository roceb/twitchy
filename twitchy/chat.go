package main

import (
	"bufio"
	"crypto/tls"
	"flag"
	"fmt"
	"os"

	irc "github.com/thoj/go-ircevent"
)

var channel string

// const channel = "#dapperedking"
const serverssl = "irc.chat.twitch.tv:6697"

func sendMessage(irccon *irc.Connection, channel string) {
	for irccon.Connected() {
		fmt.Print(">")
		reader := bufio.NewReader(os.Stdin)
		text, _ := reader.ReadString('\n')
		irccon.Privmsg(channel, text)
	}
}

func main() {
	wordPtr := flag.String("c", "", "channel")
	authPtr := flag.String("p", "", "oauth password")
	nickPtr := flag.String("n", "", "nickname")
	debug := flag.Bool("l", false, "enables debugging mode")
	flag.Parse()
	var channel string = *wordPtr
	ircnick1 := *nickPtr
	irccon := irc.IRC(ircnick1, ircnick1)
	irccon.Password = *authPtr
	irccon.VerboseCallbackHandler = false
	irccon.Debug = *debug
	irccon.UseTLS = true
	irccon.TLSConfig = &tls.Config{InsecureSkipVerify: true}
	irccon.AddCallback("001", func(e *irc.Event) { irccon.Join(channel) })
	irccon.AddCallback("PRIVMSG", func(event *irc.Event) {
		fmt.Printf("%s: %s\n", event.Nick, event.Message())
		//		sendMessage(irccon)
	})
	irccon.AddCallback("PRIVMSG", func(e *irc.Event) {
		go func(e *irc.Event) {

			//		for irccon.Connected() {
			//	sendMessage(irccon, channel)
			//		}
		}(e)
	})
	err := irccon.Connect(serverssl)
	sendMessage(irccon, channel)
	if err != nil {
		fmt.Printf("Err %s", err)
		return
	}
	irccon.Loop()
}
