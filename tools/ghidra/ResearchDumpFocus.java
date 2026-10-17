// Export selected functions and their callers for local reverse engineering.
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.nio.file.*;
import java.io.*;
import java.util.*;

public class ResearchDumpFocus extends GhidraScript {
    public void run() throws Exception {
        String[] args = getScriptArgs();
        boolean only = args.length > 1 && args[1].equals("ONLY");
        Path output = Paths.get(args[0]);
        Files.createDirectories(output);
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        LinkedHashSet<Function> selected = new LinkedHashSet<>();
        try (PrintWriter index = new PrintWriter(Files.newBufferedWriter(output.resolve("function-index.tsv")))) {
            FunctionIterator functions = currentProgram.getFunctionManager().getFunctions(true);
            while (functions.hasNext()) {
                Function f = functions.next();
                index.printf("%s\t%d\t%s%n", f.getEntryPoint(), f.getBody().getNumAddresses(), f.getName());
            }
        }
        try (PrintWriter refs = new PrintWriter(Files.newBufferedWriter(output.resolve("focus-references.txt")))) {
            for (int i = only ? 2 : 1; i < args.length; i++) {
                Address address = toAddr(args[i]);
                Function f = getFunctionContaining(address);
                refs.println("FOCUS " + address + " FUNCTION " + (f == null ? "NONE" : f.getEntryPoint() + " " + f.getName()));
                if (f != null) selected.add(f);
                if (only) continue;
                ReferenceIterator references = currentProgram.getReferenceManager().getReferencesTo(address);
                while (references.hasNext()) {
                    Reference ref = references.next();
                    Function caller = getFunctionContaining(ref.getFromAddress());
                    refs.println("  REF " + ref.getFromAddress() + " " + ref.getReferenceType() + " IN " + (caller == null ? "NONE" : caller.getEntryPoint() + " " + caller.getName()));
                    if (caller != null) selected.add(caller);
                }
                if (f != null && !address.equals(f.getEntryPoint())) {
                    references = currentProgram.getReferenceManager().getReferencesTo(f.getEntryPoint());
                    while (references.hasNext()) {
                        Reference ref = references.next();
                        Function caller = getFunctionContaining(ref.getFromAddress());
                        refs.println("  CALLER " + ref.getFromAddress() + " IN " + (caller == null ? "NONE" : caller.getEntryPoint() + " " + caller.getName()));
                        if (caller != null) selected.add(caller);
                    }
                }
            }
        }
        int count = 0;
        for (Function f : selected) {
            monitor.checkCancelled();
            DecompileResults result = decompiler.decompileFunction(f, 45, monitor);
            Path file = output.resolve(f.getEntryPoint().toString() + ".c");
            String text = "// " + f.getName() + " at " + f.getEntryPoint() + "\n";
            if (result.decompileCompleted()) text += result.getDecompiledFunction().getC();
            else text += "// Decompiler error: " + result.getErrorMessage() + "\n";
            Files.writeString(file, text);
            println("Exported " + file);
            count++;
        }
        println("Functions exported: " + count);
        decompiler.dispose();
    }
}
