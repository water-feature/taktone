// Assemble instruction requests without modifying the firmware project.
import ghidra.app.script.GhidraScript;
import ghidra.app.plugin.assembler.*;
import java.nio.file.*;
import java.util.*;

public class TaktoneAssembleBatch extends GhidraScript {
    public void run() throws Exception {
        String[] args = getScriptArgs();
        Assembler assembler = Assemblers.getAssembler(currentProgram);
        StringBuilder out = new StringBuilder();
        for (String request : Files.readAllLines(Path.of(args[0]))) {
            if (request.isBlank()) continue;
            String[] fields = request.split("\t", 2);
            try {
                byte[] bytes = assembler.assembleLine(toAddr(fields[0]), fields[1]);
                out.append(fields[0]).append('\t').append(HexFormat.of().formatHex(bytes)).append('\t').append(fields[1]).append('\n');
            } catch (Exception exc) {
                throw new IllegalArgumentException("Assembly failed: " + request, exc);
            }
        }
        Files.writeString(Path.of(args[1]), out.toString());
        println("Assembled requests to " + args[1]);
    }
}
